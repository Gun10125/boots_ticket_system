"""BOOTS IT HELPDESK - database layer (SQLite, stdlib only, multi-user safe)"""
import sqlite3, os, json, datetime, hashlib, secrets, time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.environ.get("BOOTS_DB", os.path.join(DATA_DIR, "boots_helpdesk.db"))

# --- step 1: tables only (no indexes) ---
SCHEMA_TABLES = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    pwd_hash TEXT NOT NULL, salt TEXT NOT NULL,
    full_name TEXT DEFAULT '', role TEXT DEFAULT 'staff',
    email TEXT DEFAULT '', active INTEGER DEFAULT 1,
    must_change INTEGER DEFAULT 0,
    created_at TEXT DEFAULT '', last_login TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY, user_id INTEGER NOT NULL,
    created_at TEXT, expires_at TEXT, ip TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS branches (
    code TEXT PRIMARY KEY, name TEXT NOT NULL, location TEXT DEFAULT 'ไม่ระบุ',
    tel TEXT DEFAULT '', active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS masters (
    id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, value TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0, active INTEGER DEFAULT 1, UNIQUE(kind, value));
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_no TEXT NOT NULL UNIQUE, open_date TEXT NOT NULL, open_time TEXT NOT NULL,
    helpdesk TEXT DEFAULT '', service_type TEXT DEFAULT '', status TEXT DEFAULT 'Pending',
    branch_code TEXT DEFAULT '', branch_name TEXT DEFAULT '', location TEXT DEFAULT '',
    contact_name TEXT DEFAULT '', job_title TEXT DEFAULT '', phone_no TEXT DEFAULT '',
    problem_desc TEXT DEFAULT '', ticket_type TEXT DEFAULT '', category TEXT DEFAULT '',
    device TEXT DEFAULT '', software TEXT DEFAULT '', serial_no TEXT DEFAULT '',
    asset_tag TEXT DEFAULT '', hht TEXT DEFAULT '', cid_uih TEXT DEFAULT '',
    model TEXT DEFAULT '', dispatch_to TEXT DEFAULT '', vendor_name TEXT DEFAULT '',
    responsible TEXT DEFAULT '', service_order TEXT DEFAULT '', vendor_date TEXT DEFAULT '',
    vendor_time TEXT DEFAULT '', resolved_date TEXT DEFAULT '', resolved_time TEXT DEFAULT '',
    close_date TEXT DEFAULT '', close_time TEXT DEFAULT '', sla_hour TEXT DEFAULT '',
    sla_result TEXT DEFAULT 'ยังไม่ประเมิน', memo TEXT DEFAULT '', month_key TEXT DEFAULT '',
    created_by TEXT DEFAULT '', updated_by TEXT DEFAULT '',
    created_at TEXT DEFAULT '', updated_at TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS ticket_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id INTEGER NOT NULL,
    case_no TEXT DEFAULT '', action TEXT, detail TEXT, actor TEXT, at TEXT);
"""

# --- step 3: indexes, created AFTER column migration ---
SCHEMA_INDEXES = [
    ("ix_s_user", "CREATE INDEX IF NOT EXISTS ix_s_user ON sessions(user_id)"),
    ("ix_t_status", "CREATE INDEX IF NOT EXISTS ix_t_status ON tickets(status)"),
    ("ix_t_date", "CREATE INDEX IF NOT EXISTS ix_t_date ON tickets(open_date)"),
    ("ix_t_month", "CREATE INDEX IF NOT EXISTS ix_t_month ON tickets(month_key)"),
    ("ix_t_branch", "CREATE INDEX IF NOT EXISTS ix_t_branch ON tickets(branch_code)"),
    ("ix_t_creator", "CREATE INDEX IF NOT EXISTS ix_t_creator ON tickets(created_by)"),
    ("ix_l_ticket", "CREATE INDEX IF NOT EXISTS ix_l_ticket ON ticket_log(ticket_id)"),
]

# columns that may be missing in databases made by older versions
MIGRATIONS = [
    ("tickets", "created_by", "TEXT DEFAULT ''"),
    ("tickets", "updated_by", "TEXT DEFAULT ''"),
    ("tickets", "month_key", "TEXT DEFAULT ''"),
    ("tickets", "resolved_date", "TEXT DEFAULT ''"),
    ("tickets", "resolved_time", "TEXT DEFAULT ''"),
    ("ticket_log", "case_no", "TEXT DEFAULT ''"),
    ("users", "must_change", "INTEGER DEFAULT 0"),
    ("users", "last_login", "TEXT DEFAULT ''"),
    ("branches", "tel", "TEXT DEFAULT ''"),
]

ROLES = {"admin": "ผู้ดูแลระบบ", "staff": "เจ้าหน้าที่ Helpdesk", "viewer": "ดูอย่างเดียว"}


def connect():
    os.makedirs(DATA_DIR, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=30000")
    con.execute("PRAGMA synchronous=NORMAL")
    return con


def _retry(fn, *a, **kw):
    for i in range(6):
        try:
            return fn(*a, **kw)
        except sqlite3.OperationalError as e:
            if "locked" not in str(e).lower() or i == 5:
                raise
            time.sleep(0.15 * (i + 1))


def _table_exists(con, table):
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                       (table,)).fetchone() is not None


def migrate(con):
    """Add any columns missing from databases created by older versions."""
    added = []
    for table, col, decl in MIGRATIONS:
        if not _table_exists(con, table):
            continue
        cols = {r["name"] for r in con.execute("PRAGMA table_info(%s)" % table)}
        if col not in cols:
            try:
                con.execute("ALTER TABLE %s ADD COLUMN %s %s" % (table, col, decl))
                added.append("%s.%s" % (table, col))
            except sqlite3.OperationalError:
                pass
    if added:
        con.commit()
        print("  [migrate] added columns: %s" % ", ".join(added))
    return added


def init_db():
    con = connect()
    try:
        # 1. create tables
        con.executescript(SCHEMA_TABLES)
        con.commit()
        # 2. upgrade old databases BEFORE touching indexes
        migrate(con)
        # 3. now indexes are safe
        for name, sql in SCHEMA_INDEXES:
            try:
                con.execute(sql)
            except sqlite3.OperationalError as e:
                print("  [warn] skip index %s : %s" % (name, e))
        con.commit()
        # 4. seed defaults
        seed(con)
    finally:
        con.close()


def seed(con):
    if con.execute("SELECT COUNT(*) c FROM masters").fetchone()["c"] == 0:
        p = os.path.join(BASE_DIR, "masters.json")
        if os.path.exists(p):
            for kind, values in json.load(open(p, encoding="utf-8")).items():
                for i, v in enumerate(values):
                    con.execute("INSERT OR IGNORE INTO masters(kind,value,sort_order)"
                                " VALUES(?,?,?)", (kind, v, i))
    if con.execute("SELECT COUNT(*) c FROM branches").fetchone()["c"] == 0:
        p = os.path.join(BASE_DIR, "branches.json")
        if os.path.exists(p):
            try:
                for b in json.load(open(p, encoding="utf-8")):
                    con.execute("INSERT OR IGNORE INTO branches(code,name,location,tel)"
                                " VALUES(?,?,?,?)",
                                (b["code"], b["name"], b.get("location", "ไม่ระบุ"),
                                 b.get("tel", "")))
            except Exception:
                pass
    if con.execute("SELECT COUNT(*) c FROM users").fetchone()["c"] == 0:
        salt = secrets.token_hex(16)
        con.execute("INSERT INTO users(username,pwd_hash,salt,full_name,role,active,"
                    "must_change,created_at) VALUES(?,?,?,?,?,1,1,?)",
                    ("admin", _hash("admin123", salt), salt, "ผู้ดูแลระบบ", "admin", _now()))
    con.commit()


def _hash(pwd, salt):
    return hashlib.pbkdf2_hmac("sha256", pwd.encode("utf-8"),
                               salt.encode("utf-8"), 120000).hex()


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def verify_login(username, password):
    con = connect()
    u = con.execute("SELECT * FROM users WHERE username=? AND active=1",
                    (username.strip(),)).fetchone()
    con.close()
    if not u:
        return None
    if not secrets.compare_digest(_hash(password, u["salt"]), u["pwd_hash"]):
        return None
    return dict(u)


def session_create(user_id, ip="", days=7):
    token = secrets.token_urlsafe(32)
    exp = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    con = connect()
    con.execute("INSERT INTO sessions(token,user_id,created_at,expires_at,ip) VALUES(?,?,?,?,?)",
                (token, user_id, _now(), exp, ip))
    con.execute("UPDATE users SET last_login=? WHERE id=?", (_now(), user_id))
    con.execute("DELETE FROM sessions WHERE expires_at<?", (_now(),))
    con.commit(); con.close()
    return token


def session_user(token):
    if not token:
        return None
    con = connect()
    r = con.execute(
        "SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id "
        "WHERE s.token=? AND s.expires_at>? AND u.active=1",
        (token, _now())).fetchone()
    con.close()
    return dict(r) if r else None


def session_delete(token):
    con = connect()
    con.execute("DELETE FROM sessions WHERE token=?", (token,))
    con.commit(); con.close()


def users_all():
    con = connect()
    rows = con.execute("SELECT id,username,full_name,role,email,active,last_login,"
                       "created_at FROM users ORDER BY active DESC, username").fetchall()
    con.close()
    return [dict(r) for r in rows]


def user_get(uid):
    con = connect()
    r = con.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    con.close()
    return dict(r) if r else None


def user_create(username, password, full_name, role="staff", email=""):
    username = (username or "").strip()
    if not username or not password:
        raise ValueError("ต้องกรอกชื่อผู้ใช้และรหัสผ่าน")
    if len(password) < 6:
        raise ValueError("รหัสผ่านต้องยาวอย่างน้อย 6 ตัวอักษร")
    if role not in ROLES:
        role = "staff"
    con = connect()
    if con.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
        con.close()
        raise ValueError("ชื่อผู้ใช้นี้มีอยู่แล้ว: %s" % username)
    salt = secrets.token_hex(16)
    con.execute("INSERT INTO users(username,pwd_hash,salt,full_name,role,email,active,"
                "must_change,created_at) VALUES(?,?,?,?,?,?,1,1,?)",
                (username, _hash(password, salt), salt, full_name.strip(), role,
                 email.strip(), _now()))
    con.commit(); con.close()


def user_update(uid, full_name, role, email, active):
    con = connect()
    con.execute("UPDATE users SET full_name=?, role=?, email=?, active=? WHERE id=?",
                (full_name.strip(), role if role in ROLES else "staff",
                 email.strip(), 1 if active else 0, uid))
    con.commit(); con.close()


def user_set_password(uid, password, must_change=0, keep_token=None):
    if len(password or "") < 6:
        raise ValueError("รหัสผ่านต้องยาวอย่างน้อย 6 ตัวอักษร")
    salt = secrets.token_hex(16)
    con = connect()
    con.execute("UPDATE users SET pwd_hash=?, salt=?, must_change=? WHERE id=?",
                (_hash(password, salt), salt, must_change, uid))
    if keep_token:
        con.execute("DELETE FROM sessions WHERE user_id=? AND token<>?", (uid, keep_token))
    else:
        con.execute("DELETE FROM sessions WHERE user_id=?", (uid,))
    con.commit(); con.close()


def admin_count():
    con = connect()
    n = con.execute("SELECT COUNT(*) c FROM users WHERE role='admin' AND active=1").fetchone()["c"]
    con.close()
    return n


def master_list(kind):
    con = connect()
    rows = con.execute("SELECT value FROM masters WHERE kind=? AND active=1 "
                       "ORDER BY sort_order, value", (kind,)).fetchall()
    con.close()
    return [r["value"] for r in rows]


def all_masters():
    kinds = ["helpdesk", "service_type", "status", "type", "location", "category",
             "device", "vendor", "responsible", "dispatch", "job_title",
             "sla_result", "sla_hour"]
    return {k: master_list(k) for k in kinds}


def master_add(kind, value):
    if not (value or "").strip():
        return
    con = connect()
    con.execute("INSERT OR IGNORE INTO masters(kind,value,sort_order) VALUES(?,?,999)",
                (kind, value.strip()))
    con.commit(); con.close()


def master_delete(kind, value):
    con = connect()
    con.execute("DELETE FROM masters WHERE kind=? AND value=?", (kind, value))
    con.commit(); con.close()


def branches():
    con = connect()
    rows = con.execute("SELECT code,name,location,tel FROM branches WHERE active=1 "
                       "ORDER BY code").fetchall()
    con.close()
    return [dict(r) for r in rows]


def branch_get(code):
    con = connect()
    r = con.execute("SELECT code,name,location,tel FROM branches WHERE code=?",
                    (code,)).fetchone()
    con.close()
    return dict(r) if r else None


def branch_add(code, name, location, tel=""):
    con = connect()
    con.execute("INSERT OR REPLACE INTO branches(code,name,location,tel) VALUES(?,?,?,?)",
                (code.strip(), name.strip(), location, tel))
    con.commit(); con.close()


FIELDS = ["case_no", "open_date", "open_time", "helpdesk", "service_type", "status",
          "branch_code", "branch_name", "location", "contact_name", "job_title",
          "phone_no", "problem_desc", "ticket_type", "category", "device", "software",
          "serial_no", "asset_tag", "hht", "cid_uih", "model", "dispatch_to",
          "vendor_name", "responsible", "service_order", "vendor_date", "vendor_time",
          "resolved_date", "resolved_time", "close_date", "close_time", "sla_hour",
          "sla_result", "memo"]


def _mk(d):
    try:
        return d[:7].replace("-", "")
    except Exception:
        return ""


def _create(data, actor):
    d = {k: (data.get(k) or "").strip() for k in FIELDS}
    con = connect()
    try:
        if con.execute("SELECT id FROM tickets WHERE case_no=?", (d["case_no"],)).fetchone():
            raise ValueError("เลข Ticket นี้มีอยู่แล้วในระบบ: %s" % d["case_no"])
        cols = FIELDS + ["month_key", "created_by", "updated_by", "created_at", "updated_at"]
        vals = [d[f] for f in FIELDS] + [_mk(d["open_date"]), actor, actor, _now(), _now()]
        try:
            cur = con.execute("INSERT INTO tickets(%s) VALUES(%s)"
                              % (",".join(cols), ",".join("?" * len(cols))), vals)
        except sqlite3.IntegrityError:
            raise ValueError("เลข Ticket นี้เพิ่งถูกบันทึกโดยผู้ใช้อื่น: %s" % d["case_no"])
        tid = cur.lastrowid
        con.execute("INSERT INTO ticket_log(ticket_id,case_no,action,detail,actor,at) "
                    "VALUES(?,?,?,?,?,?)",
                    (tid, d["case_no"], "CREATE", "เปิดงานใหม่", actor, _now()))
        con.commit()
        return tid
    finally:
        con.close()


def ticket_create(data, actor=""):
    return _retry(_create, data, actor)


def _update(tid, data, actor):
    d = {k: (data.get(k) or "").strip() for k in FIELDS}
    con = connect()
    try:
        old = con.execute("SELECT * FROM tickets WHERE id=?", (tid,)).fetchone()
        sets = ",".join("%s=?" % f for f in FIELDS)
        vals = [d[f] for f in FIELDS] + [_mk(d["open_date"]), actor, _now(), tid]
        con.execute("UPDATE tickets SET %s, month_key=?, updated_by=?, updated_at=? "
                    "WHERE id=?" % sets, vals)
        if old:
            chg = []
            if old["status"] != d["status"]:
                chg.append("สถานะ %s -> %s" % (old["status"], d["status"]))
            for f, label in (("vendor_name", "Vendor"), ("category", "Category"),
                             ("sla_result", "SLA")):
                if (old[f] or "") != d[f]:
                    chg.append("%s %s -> %s" % (label, old[f] or "-", d[f] or "-"))
            if chg:
                con.execute("INSERT INTO ticket_log(ticket_id,case_no,action,detail,actor,at) "
                            "VALUES(?,?,?,?,?,?)",
                            (tid, d["case_no"], "UPDATE", " / ".join(chg), actor, _now()))
        con.commit()
    finally:
        con.close()


def ticket_update(tid, data, actor=""):
    return _retry(_update, tid, data, actor)


def ticket_get(tid):
    con = connect()
    r = con.execute("SELECT * FROM tickets WHERE id=?", (tid,)).fetchone()
    con.close()
    return dict(r) if r else None


def ticket_history(tid, limit=30):
    con = connect()
    rows = con.execute("SELECT action,detail,actor,at FROM ticket_log WHERE ticket_id=? "
                       "ORDER BY id DESC LIMIT ?", (tid, limit)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def ticket_delete(tid, actor=""):
    con = connect()
    t = con.execute("SELECT case_no FROM tickets WHERE id=?", (tid,)).fetchone()
    con.execute("DELETE FROM tickets WHERE id=?", (tid,))
    con.execute("INSERT INTO ticket_log(ticket_id,case_no,action,detail,actor,at) "
                "VALUES(?,?,?,?,?,?)",
                (tid, t["case_no"] if t else "", "DELETE", "ลบงาน", actor, _now()))
    con.commit(); con.close()


def ticket_search(f, limit=50, offset=0,
                  order="open_date DESC, open_time DESC, id DESC"):
    w, p = [], []
    simple = [("status", "status"), ("helpdesk", "helpdesk"), ("category", "category"),
              ("vendor", "vendor_name"), ("location", "location"),
              ("ticket_type", "ticket_type"), ("sla_result", "sla_result"),
              ("created_by", "created_by")]
    for key, col in simple:
        if f.get(key):
            w.append("%s=?" % col); p.append(f[key])
    if f.get("branch"):
        w.append("(branch_code=? OR branch_name LIKE ?)")
        p += [f["branch"], "%%%s%%" % f["branch"]]
    if f.get("date_from"):
        w.append("open_date>=?"); p.append(f["date_from"])
    if f.get("date_to"):
        w.append("open_date<=?"); p.append(f["date_to"])
    if f.get("month"):
        w.append("month_key=?"); p.append(f["month"].replace("-", ""))
    if f.get("q"):
        like = "%%%s%%" % f["q"]
        w.append("(case_no LIKE ? OR problem_desc LIKE ? OR branch_name LIKE ? "
                 "OR contact_name LIKE ? OR memo LIKE ? OR category LIKE ?)")
        p += [like] * 6
    where = ("WHERE " + " AND ".join(w)) if w else ""
    con = connect()
    total = con.execute("SELECT COUNT(*) c FROM tickets %s" % where, p).fetchone()["c"]
    rows = con.execute("SELECT * FROM tickets %s ORDER BY %s LIMIT ? OFFSET ?"
                       % (where, order), p + [limit, offset]).fetchall()
    con.close()
    return [dict(r) for r in rows], total


def dashboard_stats(username="", day=None, month=None):
    day = day or datetime.date.today().isoformat()
    month = month or day[:7].replace("-", "")
    con = connect()
    q = lambda s, p=(): con.execute(s, p).fetchone()["c"]
    out = {
        "today": q("SELECT COUNT(*) c FROM tickets WHERE open_date=?", (day,)),
        "month": q("SELECT COUNT(*) c FROM tickets WHERE month_key=?", (month,)),
        "pending": q("SELECT COUNT(*) c FROM tickets WHERE status='Pending'"),
        "checking": q("SELECT COUNT(*) c FROM tickets WHERE status='Checking'"),
        "resolved": q("SELECT COUNT(*) c FROM tickets WHERE status='Resolved'"),
        "closed": q("SELECT COUNT(*) c FROM tickets WHERE status='Close'"),
        "total": q("SELECT COUNT(*) c FROM tickets"),
        "mine_open": q("SELECT COUNT(*) c FROM tickets WHERE created_by=? "
                       "AND status IN ('Pending','Checking')", (username,)),
        "mine_today": q("SELECT COUNT(*) c FROM tickets WHERE created_by=? AND open_date=?",
                        (username, day)),
        "out_sla": q("SELECT COUNT(*) c FROM tickets WHERE sla_result='OUT SLA' "
                     "AND month_key=?", (month,)),
        "in_sla": q("SELECT COUNT(*) c FROM tickets WHERE sla_result='IN SLA' "
                    "AND month_key=?", (month,)),
        "users_online": q("SELECT COUNT(DISTINCT user_id) c FROM sessions WHERE expires_at>?",
                          (_now(),)),
    }
    out["top_category"] = [dict(r) for r in con.execute(
        "SELECT category k, COUNT(*) c FROM tickets WHERE month_key=? AND category<>'' "
        "GROUP BY category ORDER BY c DESC LIMIT 8", (month,)).fetchall()]
    out["top_branch"] = [dict(r) for r in con.execute(
        "SELECT branch_name k, COUNT(*) c FROM tickets WHERE month_key=? "
        "AND branch_name<>'' GROUP BY branch_name ORDER BY c DESC LIMIT 8",
        (month,)).fetchall()]
    out["by_user"] = [dict(r) for r in con.execute(
        "SELECT created_by k, COUNT(*) c FROM tickets WHERE month_key=? AND created_by<>'' "
        "GROUP BY created_by ORDER BY c DESC", (month,)).fetchall()]
    out["last7"] = [dict(r) for r in con.execute(
        "SELECT open_date k, COUNT(*) c FROM tickets WHERE open_date>=? "
        "GROUP BY open_date ORDER BY open_date",
        ((datetime.date.today() - datetime.timedelta(days=6)).isoformat(),)).fetchall()]
    out["recent"] = [dict(r) for r in con.execute(
        "SELECT case_no,action,detail,actor,at FROM ticket_log ORDER BY id DESC LIMIT 8"
    ).fetchall()]
    con.close()
    return out


def report_group(month, group_by):
    col = {"category": "category", "vendor": "vendor_name", "helpdesk": "helpdesk",
           "branch": "branch_name", "type": "ticket_type", "status": "status",
           "location": "location", "sla": "sla_result",
           "user": "created_by"}.get(group_by, "category")
    con = connect()
    rows = con.execute("SELECT %s k, COUNT(*) c FROM tickets WHERE month_key=? "
                       "GROUP BY %s ORDER BY c DESC" % (col, col),
                       (month.replace("-", ""),)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def report_daily(month):
    con = connect()
    rows = con.execute(
        "SELECT open_date k, COUNT(*) total, "
        "SUM(CASE WHEN status='Close' THEN 1 ELSE 0 END) closed, "
        "SUM(CASE WHEN status='Resolved' THEN 1 ELSE 0 END) resolved, "
        "SUM(CASE WHEN status IN ('Pending','Checking') THEN 1 ELSE 0 END) pending, "
        "SUM(CASE WHEN sla_result='OUT SLA' THEN 1 ELSE 0 END) out_sla "
        "FROM tickets WHERE month_key=? GROUP BY open_date ORDER BY open_date",
        (month.replace("-", ""),)).fetchall()
    con.close()
    return [dict(r) for r in rows]
