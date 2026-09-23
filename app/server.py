"""
BOOTS IT HELPDESK - Ticket System
Multi-user web server with login (Python standard library only)
"""
import os, sys, io, csv, json, datetime, urllib.parse, socket, traceback, http.cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db, ui

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(BASE_DIR, "static")
PER_PAGE = 50
COOKIE = "boots_sid"
FILTER_KEYS = ("status", "helpdesk", "category", "vendor", "location", "ticket_type",
               "sla_result", "date_from", "date_to", "month", "q", "created_by")


def qs_parse(q):
    return {k: v[0] for k, v in urllib.parse.parse_qs(q, keep_blank_values=False).items()}


def build_qs(f):
    return urllib.parse.urlencode({k: v for k, v in f.items() if v})


class Handler(BaseHTTPRequestHandler):
    server_version = "BootsHelpdesk/2.1"
    protocol_version = "HTTP/1.1"

    def _send(self, data, ctype, code=200, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        if extra:
            for k, v in extra:
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def send_html(self, s, code=200, extra=None):
        self._send(s.encode("utf-8"), "text/html; charset=utf-8", code,
                   (extra or []) + [("Cache-Control", "no-store")])

    def send_json(self, obj):
        self._send(json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def redirect(self, url, extra=None):
        self.send_response(303)
        self.send_header("Location", url)
        self.send_header("Content-Length", "0")
        if extra:
            for k, v in extra:
                self.send_header(k, v)
        self.end_headers()

    def send_static(self, path):
        fp = os.path.join(STATIC, os.path.basename(path))
        if not os.path.exists(fp):
            return self.send_html("<h1>404</h1>", 404)
        ctype = "text/css" if fp.endswith(".css") else "application/javascript"
        self._send(open(fp, "rb").read(), ctype + "; charset=utf-8", 200,
                   [("Cache-Control", "max-age=3600")])

    def read_post(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n).decode("utf-8") if n else ""
        return {k: v[0] for k, v in urllib.parse.parse_qs(raw, keep_blank_values=True).items()}

    def cookie_get(self):
        raw = self.headers.get("Cookie")
        if not raw:
            return None
        try:
            c = http.cookies.SimpleCookie(raw)
            return c[COOKIE].value if COOKIE in c else None
        except Exception:
            return None

    def client_ip(self):
        return self.client_address[0] if self.client_address else ""

    def log_message(self, *a):
        pass

    def current_user(self):
        return db.session_user(self.cookie_get())

    def need_role(self, user, *roles):
        if user.get("role") in roles:
            return True
        self.send_html(ui.page_denied(user), 403)
        return False

    def do_GET(self):
        try:
            u = urllib.parse.urlparse(self.path)
            p, q = u.path, qs_parse(u.query)

            if p.startswith("/static/"):
                return self.send_static(p)
            if p == "/login":
                if self.current_user():
                    return self.redirect("/")
                return self.send_html(ui.page_login())
            if p == "/logout":
                tok = self.cookie_get()
                if tok:
                    db.session_delete(tok)
                return self.redirect("/login", [("Set-Cookie",
                    "%s=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax" % COOKIE)])

            user = self.current_user()
            if not user:
                return self.redirect("/login")
            if user.get("must_change") and p != "/profile":
                return self.send_html(ui.page_change_pwd(user, forced=True))

            if p == "/":
                today = datetime.date.today().isoformat()
                return self.send_html(ui.page_dashboard(
                    db.dashboard_stats(user["username"]), today, user))

            if p == "/profile":
                return self.send_html(ui.page_change_pwd(user))

            if p == "/tickets":
                f = {k: q.get(k, "") for k in FILTER_KEYS}
                try:
                    page = max(1, int(q.get("page", 1)))
                except ValueError:
                    page = 1
                rows, total = db.ticket_search(f, PER_PAGE, (page - 1) * PER_PAGE)
                names = [x["username"] for x in db.users_all() if x["active"]]
                return self.send_html(ui.page_tickets(rows, total, f, db.all_masters(),
                                                      page, PER_PAGE, build_qs(f),
                                                      user, names))

            if p == "/tickets/new":
                if user["role"] == "viewer":
                    return self.send_html(ui.page_denied(user), 403)
                return self.send_html(ui.ticket_form(db.all_masters(), db.branches(), user))

            if p.startswith("/tickets/") and p.endswith("/delete"):
                if not self.need_role(user, "admin"):
                    return
                db.ticket_delete(int(p.split("/")[2]), user["username"])
                return self.redirect("/tickets")

            if p.startswith("/tickets/"):
                tid = int(p.split("/")[2])
                t = db.ticket_get(tid)
                if not t:
                    return self.send_html(ui.layout("ไม่พบงาน",
                        "<div class='card'><h1>ไม่พบงานนี้</h1>"
                        "<a class='btn' href='/tickets'>กลับ</a></div>", "", user), 404)
                return self.send_html(ui.ticket_form(db.all_masters(), db.branches(),
                                                     user, t, "", db.ticket_history(tid)))

            if p == "/reports":
                month = q.get("month") or datetime.date.today().strftime("%Y-%m")
                groups = {g: db.report_group(month, g)
                          for g in ("category", "vendor", "user", "branch")}
                return self.send_html(ui.page_reports(month, db.report_daily(month),
                                                      groups, db.all_masters(), user))

            if p == "/masters":
                return self.send_html(ui.page_masters(db.all_masters(),
                                                      len(db.branches()), user))

            if p == "/masters/del":
                if not self.need_role(user, "admin"):
                    return
                db.master_delete(q.get("kind", ""), q.get("value", ""))
                return self.redirect("/masters")

            if p == "/users":
                if not self.need_role(user, "admin"):
                    return
                return self.send_html(ui.page_users(db.users_all(), user,
                                                    q.get("err", ""), q.get("ok", "")))

            if p.startswith("/users/"):
                if not self.need_role(user, "admin"):
                    return
                tgt = db.user_get(int(p.split("/")[2]))
                if not tgt:
                    return self.redirect("/users")
                return self.send_html(ui.page_user_edit(tgt, user, q.get("err", ""),
                                                        q.get("ok", "")))

            if p == "/api/branch":
                return self.send_json(db.branch_get(q.get("code", "")) or {})

            if p == "/export.csv":
                return self.export_csv(q)

            return self.send_html(ui.layout("404",
                "<div class='card'><h1>ไม่พบหน้านี้</h1>"
                "<a class='btn' href='/'>กลับหน้าหลัก</a></div>", "", user), 404)
        except Exception:
            return self.send_html("<pre style='padding:20px'>%s</pre>"
                                  % traceback.format_exc(), 500)

    def do_POST(self):
        try:
            p = urllib.parse.urlparse(self.path).path
            form = self.read_post()

            if p == "/login":
                usr = db.verify_login(form.get("username", ""), form.get("password", ""))
                if not usr:
                    return self.send_html(ui.page_login(
                        "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง", "",
                        form.get("username", "")), 401)
                tok = db.session_create(usr["id"], self.client_ip())
                return self.redirect("/", [("Set-Cookie",
                    "%s=%s; Path=/; Max-Age=604800; HttpOnly; SameSite=Lax" % (COOKIE, tok))])

            user = self.current_user()
            if not user:
                return self.redirect("/login")

            if p == "/profile":
                old = form.get("old_pwd", "")
                new = form.get("new_pwd", "")
                if not db.verify_login(user["username"], old):
                    return self.send_html(ui.page_change_pwd(
                        user, "รหัสผ่านเดิมไม่ถูกต้อง", bool(user.get("must_change"))))
                if new != form.get("new_pwd2", ""):
                    return self.send_html(ui.page_change_pwd(
                        user, "รหัสผ่านใหม่ทั้งสองช่องไม่ตรงกัน",
                        bool(user.get("must_change"))))
                try:
                    db.user_set_password(user["id"], new, must_change=0,
                                         keep_token=self.cookie_get())
                except ValueError as e:
                    return self.send_html(ui.page_change_pwd(
                        user, str(e), bool(user.get("must_change"))))
                return self.redirect("/")

            if user.get("must_change"):
                return self.send_html(ui.page_change_pwd(user, forced=True))

            if p == "/tickets/new":
                if user["role"] == "viewer":
                    return self.send_html(ui.page_denied(user), 403)
                try:
                    tid = db.ticket_create(form, user["username"])
                except ValueError as e:
                    return self.send_html(ui.ticket_form(db.all_masters(), db.branches(),
                                                         user, form, str(e)))
                return self.send_html(ui.page_saved(form.get("case_no", ""), tid, user))

            if p.startswith("/tickets/"):
                if user["role"] == "viewer":
                    return self.send_html(ui.page_denied(user), 403)
                tid = int(p.split("/")[2])
                db.ticket_update(tid, form, user["username"])
                return self.redirect("/tickets/%d" % tid)

            if p == "/masters/add":
                if not self.need_role(user, "admin"):
                    return
                db.master_add(form.get("kind", ""), form.get("value", ""))
                return self.redirect("/masters")

            if p == "/masters/branch":
                if not self.need_role(user, "admin"):
                    return
                db.branch_add(form.get("code", ""), form.get("name", ""),
                              form.get("location", "BKK"), form.get("tel", ""))
                return self.redirect("/masters")

            if p == "/users/new":
                if not self.need_role(user, "admin"):
                    return
                try:
                    db.user_create(form.get("username", ""), form.get("password", ""),
                                   form.get("full_name", ""), form.get("role", "staff"),
                                   form.get("email", ""))
                except ValueError as e:
                    return self.redirect("/users?err=" + urllib.parse.quote(str(e)))
                return self.redirect("/users?ok=" + urllib.parse.quote(
                    "สร้างบัญชี %s เรียบร้อย" % form.get("username", "")))

            if p.startswith("/users/") and p.endswith("/pwd"):
                if not self.need_role(user, "admin"):
                    return
                uid = int(p.split("/")[2])
                try:
                    db.user_set_password(uid, form.get("password", ""), must_change=1)
                except ValueError as e:
                    return self.redirect("/users/%d?err=%s" % (uid, urllib.parse.quote(str(e))))
                return self.redirect("/users/%d?ok=%s" % (uid, urllib.parse.quote(
                    "ตั้งรหัสผ่านใหม่เรียบร้อย")))

            if p.startswith("/users/"):
                if not self.need_role(user, "admin"):
                    return
                uid = int(p.split("/")[2])
                active = form.get("active", "ใช้งาน") == "ใช้งาน"
                role = form.get("role", "staff")
                tgt = db.user_get(uid)
                if tgt and tgt["role"] == "admin" and (role != "admin" or not active) \
                        and db.admin_count() <= 1:
                    return self.redirect("/users/%d?err=%s" % (uid, urllib.parse.quote(
                        "ต้องมีผู้ดูแลระบบอย่างน้อย 1 บัญชี")))
                db.user_update(uid, form.get("full_name", ""), role,
                               form.get("email", ""), active)
                return self.redirect("/users/%d?ok=%s" % (uid, urllib.parse.quote("บันทึกแล้ว")))

            return self.send_html("<h1>404</h1>", 404)
        except Exception:
            return self.send_html("<pre style='padding:20px'>%s</pre>"
                                  % traceback.format_exc(), 500)

    def export_csv(self, q):
        f = {k: q.get(k, "") for k in FILTER_KEYS}
        rows, _ = db.ticket_search(f, limit=200000, offset=0,
                                   order="open_date ASC, open_time ASC")
        head = ["Ticket", "วันที่", "เวลา", "Helpdesk", "ServiceType", "สถานะ",
                "รหัสสาขา", "ชื่อสาขา", "Location", "ผู้ติดต่อ", "ตำแหน่ง", "เบอร์",
                "อาการ", "Type", "Category", "อุปกรณ์", "Software", "Serial", "AssetTag",
                "HHT", "CID", "รุ่น", "ส่งต่อ", "Vendor", "ผู้รับผิดชอบ", "ServiceOrder",
                "วันแจ้งVendor", "เวลาแจ้งVendor", "วันแก้เสร็จ", "เวลาแก้เสร็จ",
                "วันปิดงาน", "เวลาปิดงาน", "SLA(ชม.)", "ผล SLA", "บันทึก",
                "ผู้เปิดงาน", "แก้ไขล่าสุดโดย"]
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(head)
        for r in rows:
            w.writerow([r.get(k, "") for k in db.FIELDS]
                       + [r.get("created_by", ""), r.get("updated_by", "")])
        data = ("\ufeff" + buf.getvalue()).encode("utf-8")
        name = "boots_tickets_%s.csv" % datetime.datetime.now().strftime("%Y%m%d_%H%M")
        self._send(data, "text/csv; charset=utf-8", 200,
                   [("Content-Disposition", 'attachment; filename="%s"' % name)])


def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    print("  Preparing database ...")
    try:
        db.init_db()
    except Exception:
        print("\n" + "=" * 62)
        print("  [ERROR] Cannot prepare the database")
        print("=" * 62)
        traceback.print_exc()
        print("-" * 62)
        print("  How to fix:")
        print("   1. Close this window")
        print("   2. Go to folder:  app\\data")
        print("   3. Rename  boots_helpdesk.db  to  boots_helpdesk_old.db")
        print("   4. Start the server again (a fresh database is created)")
        print("   5. Run 3_IMPORT_OLD_DATA.bat to load your Excel data again")
        print("=" * 62)
        try:
            input("  Press Enter to exit...")
        except Exception:
            pass
        return
    try:
        srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    except OSError as e:
        print("\n  [ERROR] Cannot start on port %d : %s" % (port, e))
        print("  Try:  python server.py 9000\n")
        try:
            input("  Press Enter to exit...")
        except Exception:
            pass
        return
    srv.daemon_threads = True
    ip = local_ip()
    print("=" * 62)
    print("  BOOTS IT HELPDESK - Ticket System (Multi-user)")
    print("=" * 62)
    print("  On this server  : http://localhost:%d" % port)
    print("  FOR ALL STAFF   : http://%s:%d" % (ip, port))
    print("                    ^^^ give this address to your team")
    print("  Database file   : %s" % db.DB_PATH)
    print("-" * 62)
    print("  First login     : admin / admin123")
    print("                    (you must change the password immediately)")
    print("-" * 62)
    print("  Stop the system : press Ctrl + C")
    print("=" * 62)
    print("  Server is RUNNING. Keep this window open.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")


if __name__ == "__main__":
    main()
