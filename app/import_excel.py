"""Import old data from Excel (sheet LOG TICKET) - stdlib only."""
import sys, os, re, zipfile, datetime
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
RNS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

def col_index(ref):
    m = re.match(r"([A-Z]+)", ref or "")
    if not m: return 0
    n = 0
    for ch in m.group(1): n = n * 26 + (ord(ch) - 64)
    return n - 1

def to_date(v):
    s = str(v or "").strip()
    if not s: return ""
    if re.match(r"^\d{4}-\d{2}-\d{2}", s): return s[:10]
    try: f = float(s)
    except ValueError: return ""
    if f < 1: return ""
    return (datetime.date(1899, 12, 30) + datetime.timedelta(days=int(f))).isoformat()

def to_time(v):
    s = str(v or "").strip()
    if not s: return ""
    if re.match(r"^\d{1,2}:\d{2}", s): return s[:5]
    try: f = float(s)
    except ValueError: return ""
    secs = int(round((f - int(f)) * 86400))
    return "%02d:%02d" % (secs // 3600 % 24, secs % 3600 // 60)

class Book(object):
    def __init__(self, path):
        self.z = zipfile.ZipFile(path)
        self.shared = []
        if "xl/sharedStrings.xml" in self.z.namelist():
            root = ET.fromstring(self.z.read("xl/sharedStrings.xml"))
            for si in root.findall(NS + "si"):
                self.shared.append("".join(t.text or "" for t in si.iter(NS + "t")))
        wb = ET.fromstring(self.z.read("xl/workbook.xml"))
        rels = ET.fromstring(self.z.read("xl/_rels/workbook.xml.rels"))
        rmap = {r.get("Id"): r.get("Target") for r in rels}
        self.sheets = {}
        for sh in wb.find(NS + "sheets"):
            tgt = rmap.get(sh.get(RNS + "id"))
            if tgt:
                self.sheets[sh.get("name")] = "xl/" + tgt.lstrip("/").replace("xl/", "", 1)
    def rows(self, name):
        target = self.sheets.get(name)
        if not target: return
        for _, el in ET.iterparse(self.z.open(target), events=("end",)):
            if el.tag != NS + "row": continue
            cells = {}
            for c in el.findall(NS + "c"):
                i = col_index(c.get("r")); t = c.get("t")
                if t == "inlineStr":
                    v = "".join(x.text or "" for x in c.iter(NS + "t"))
                else:
                    vn = c.find(NS + "v"); v = vn.text if vn is not None else None
                    if t == "s" and v is not None: v = self.shared[int(v)]
                cells[i] = v
            if cells: yield [cells.get(i) for i in range(max(cells) + 1)]
            el.clear()

COLMAP = {2:"open_date",3:"open_time",4:"case_no",5:"helpdesk",6:"service_type",
 8:"service_order",10:"status",11:"branch_code",12:"branch_name",13:"location",
 14:"contact_name",15:"job_title",16:"phone_no",17:"problem_desc",18:"ticket_type",
 19:"category",20:"device",21:"software",22:"serial_no",23:"asset_tag",24:"hht",
 25:"cid_uih",26:"model",27:"dispatch_to",28:"vendor_name",29:"responsible",
 30:"vendor_date",31:"vendor_time",32:"close_date",33:"close_time",36:"sla_hour",
 38:"sla_result",39:"memo"}
DATE_F = {"open_date","vendor_date","close_date"}
TIME_F = {"open_time","vendor_time","close_time"}

def import_branch_phones(bk, con):
    sheet = None
    for name in bk.sheets:
        low = name.lower()
        if "สาขา" in name or "branch" in low or "store" in low:
            first = None
            for r in bk.rows(name):
                first = r; break
            if not first: continue
            head = " ".join(str(x or "") for x in first).lower()
            if "store code" in head or "telephone" in head or "store name" in head:
                sheet = name; break
    if not sheet: return 0
    n = 0
    for i, r in enumerate(bk.rows(sheet)):
        if i == 0: continue
        code = str(r[1] or "").strip() if len(r) > 1 else ""
        name = str(r[2] or "").strip() if len(r) > 2 else ""
        if not code or not name: continue
        tel = ""
        for j in (10, 9):
            if len(r) > j and r[j]:
                tel = re.sub(r"[^0-9]", "", str(r[j])); break
        row = con.execute("SELECT code,tel FROM branches WHERE code=?", (code,)).fetchone()
        if row:
            if tel and not row["tel"]:
                con.execute("UPDATE branches SET tel=? WHERE code=?", (tel, code)); n += 1
        else:
            con.execute("INSERT INTO branches(code,name,location,tel) VALUES(?,?,?,?)",
                        (code, name, "ไม่ระบุ", tel)); n += 1
    con.commit()
    return n

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        try: input("Press Enter to exit...")
        except Exception: pass
        return
    path = sys.argv[1].strip().strip('"')
    if not os.path.exists(path):
        print("File not found: %s" % path)
        try: input("Press Enter to exit...")
        except Exception: pass
        return
    db.init_db()
    print("Reading file ...")
    bk = Book(path)
    sheet = "LOG TICKET"
    if sheet not in bk.sheets:
        cand = [s for s in bk.sheets if "log" in s.lower() and "ticket" in s.lower()]
        if not cand:
            print("Sheet 'LOG TICKET' not found. Sheets in this file:")
            for s in bk.sheets: print("   -", s)
            try: input("Press Enter to exit...")
            except Exception: pass
            return
        sheet = cand[0]
    con = db.connect()
    existing = set(r[0] for r in con.execute("SELECT case_no FROM tickets"))
    ok = skip = dup = 0
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cols = db.FIELDS + ["month_key","created_by","updated_by","created_at","updated_at"]
    sql = "INSERT INTO tickets(%s) VALUES(%s)" % (",".join(cols), ",".join("?" * len(cols)))
    for i, r in enumerate(bk.rows(sheet)):
        if i == 0: continue
        rec = dict((f, "") for f in db.FIELDS)
        for j, name in COLMAP.items():
            v = r[j] if j < len(r) else None
            if v is None: continue
            v = str(v).strip()
            if name in DATE_F: v = to_date(v)
            elif name in TIME_F: v = to_time(v)
            rec[name] = v
        case = rec["case_no"]
        if not case or not re.match(r"^CS\d+", case) or not rec["open_date"]:
            skip += 1; continue
        if case in existing:
            dup += 1; continue
        if rec["status"] not in ("Pending","Checking","Resolved","Close"):
            rec["status"] = "Close" if rec["close_date"] else "Pending"
        if rec["sla_result"] not in ("IN SLA","OUT SLA"):
            rec["sla_result"] = "ยังไม่ประเมิน"
        who = rec["helpdesk"] or "import"
        vals = [rec[f] for f in db.FIELDS] + [rec["open_date"][:7].replace("-",""), who, who, now, now]
        con.execute(sql, vals)
        existing.add(case); ok += 1
        if ok % 500 == 0:
            con.commit(); print("  imported %d ..." % ok)
    con.commit()
    add = 0
    for r in con.execute("SELECT DISTINCT branch_code, branch_name, location "
                         "FROM tickets WHERE branch_code<>''").fetchall():
        if not con.execute("SELECT 1 FROM branches WHERE code=?", (r[0],)).fetchone():
            con.execute("INSERT INTO branches(code,name,location) VALUES(?,?,?)",
                        (r[0], r[1] or r[0], r[2] or "ไม่ระบุ")); add += 1
    con.commit()
    tel = import_branch_phones(bk, con)
    total = con.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
    btotal = con.execute("SELECT COUNT(*) FROM branches").fetchone()[0]
    con.close()
    print("-" * 50)
    print("Imported tickets   : %d" % ok)
    print("Duplicate skipped  : %d" % dup)
    print("Incomplete skipped : %d" % skip)
    print("Branches added     : %d" % add)
    print("Branch phone added : %d" % tel)
    print("-" * 50)
    print("Total tickets in DB: %d" % total)
    print("Total branches     : %d" % btotal)
    print("-" * 50)
    try: input("Press Enter to exit...")
    except Exception: pass

if __name__ == "__main__":
    main()
