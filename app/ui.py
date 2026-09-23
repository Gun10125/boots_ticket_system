"""HTML rendering - mobile first, multi-user."""
import html, datetime, json

ROLE_TH = {"admin": "ผู้ดูแลระบบ", "staff": "เจ้าหน้าที่ Helpdesk", "viewer": "ดูอย่างเดียว"}


def esc(v):
    return html.escape(str(v if v is not None else ""))


def layout(title, body, active="", user=None):
    nav = [("/", "หน้าหลัก", "dash"), ("/tickets", "รายการงาน", "tickets"),
           ("/tickets/new", "เปิดงานใหม่", "new"), ("/reports", "รายงาน", "reports"),
           ("/masters", "ตั้งค่า", "masters")]
    if user and user.get("role") == "admin":
        nav.append(("/users", "ผู้ใช้งาน", "users"))
    links = "".join('<a href="%s" class="%s">%s</a>' % (u, "on" if k == active else "", t)
                    for u, t, k in nav)
    who = ""
    if user:
        nm = user.get("full_name") or user["username"]
        who = ("""<div class="who">
<a href="/profile" class="avatar" title="%s">%s</a>
<div class="wtxt"><b>%s</b><span>%s</span></div>
<a class="logout" href="/logout">ออก</a></div>"""
               % (esc(nm), esc(nm[:1].upper()), esc(nm),
                  esc(ROLE_TH.get(user.get("role"), ""))))
    return """<!DOCTYPE html>
<html lang="th"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#00358e">
<meta name="mobile-web-app-capable" content="yes">
<title>%s | BOOTS IT HELPDESK</title>
<link rel="stylesheet" href="/static/style.css">
</head><body>
<header class="topbar">
 <button class="burger" onclick="document.getElementById('nav').classList.toggle('open')">&#9776;</button>
 <div class="brand"><span class="logo">B</span> IT HELPDESK</div>
 <a class="quick" href="/tickets/new">+ เปิดงาน</a>
</header>
<nav id="nav" class="nav">%s%s</nav>
<main>%s</main>
<footer class="ft">BOOTS Retail IT Helpdesk &middot; Ricoh Thailand &middot; %s</footer>
<script src="/static/app.js"></script>
</body></html>""" % (esc(title), links, who, body,
                     datetime.date.today().strftime("%d/%m/%Y"))


def select(name, options, value="", required=False, blank="-- เลือก --"):
    opts = ['<option value="">%s</option>' % esc(blank)] if blank is not None else []
    seen = False
    for o in options:
        sel = " selected" if str(o) == str(value) else ""
        if sel:
            seen = True
        opts.append('<option value="%s"%s>%s</option>' % (esc(o), sel, esc(o)))
    if value and not seen:
        opts.append('<option value="%s" selected>%s</option>' % (esc(value), esc(value)))
    return '<select name="%s" id="%s"%s>%s</select>' % (
        esc(name), esc(name), " required" if required else "", "".join(opts))


def field(label, control, hint=""):
    h = '<small class="hint">%s</small>' % esc(hint) if hint else ""
    return '<label class="fld"><span>%s</span>%s%s</label>' % (esc(label), control, h)


def text(name, value="", ph="", required=False, type_="text", attrs=""):
    return ('<input type="%s" name="%s" id="%s" value="%s" placeholder="%s"%s %s>'
            % (type_, esc(name), esc(name), esc(value), esc(ph),
               " required" if required else "", attrs))


def textarea(name, value="", rows=3, ph=""):
    return '<textarea name="%s" id="%s" rows="%d" placeholder="%s">%s</textarea>' % (
        esc(name), esc(name), rows, esc(ph), esc(value))


STATUS_CLASS = {"Pending": "st-pending", "Checking": "st-checking",
                "Resolved": "st-resolved", "Close": "st-close"}
STATUS_TH = {"Pending": "รอดำเนินการ", "Checking": "กำลังตรวจสอบ",
             "Resolved": "แก้ไขแล้ว", "Close": "ปิดงาน"}


def badge(s):
    return '<span class="badge %s">%s</span>' % (STATUS_CLASS.get(s, "st-pending"),
                                                 esc(STATUS_TH.get(s, s or "-")))


def sla_badge(v):
    c = {"IN SLA": "sla-in", "OUT SLA": "sla-out"}.get(v, "sla-na")
    return '<span class="badge %s">%s</span>' % (c, esc(v or "ยังไม่ประเมิน"))


def page_login(error="", info="", username=""):
    err = '<div class="alert">%s</div>' % esc(error) if error else ""
    inf = '<div class="alert ok">%s</div>' % esc(info) if info else ""
    return """<!DOCTYPE html>
<html lang="th"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#00358e">
<title>เข้าสู่ระบบ | BOOTS IT HELPDESK</title>
<link rel="stylesheet" href="/static/style.css">
</head><body class="loginbg">
<div class="loginwrap"><div class="loginbox">
 <div class="lgbrand"><span class="logo big">B</span>
  <h1>BOOTS IT HELPDESK</h1><p>ระบบเปิดงาน Ticket</p></div>
 %s%s
 <form method="post" action="/login">%s%s
  <button class="btn ok wide" type="submit">เข้าสู่ระบบ</button></form>
 <p class="lgnote">ลืมรหัสผ่าน? ติดต่อผู้ดูแลระบบเพื่อรีเซ็ตให้</p>
</div></div></body></html>""" % (
        err, inf,
        field("ชื่อผู้ใช้", text("username", username, "เช่น mayjaree", True,
                                attrs='autocomplete="username" autocapitalize="off"')),
        field("รหัสผ่าน", text("password", "", "", True, type_="password",
                               attrs='autocomplete="current-password"')))


def page_change_pwd(user, error="", forced=False):
    err = '<div class="alert">%s</div>' % esc(error) if error else ""
    note = ('<div class="alert ok">กรุณาตั้งรหัสผ่านใหม่ก่อนเริ่มใช้งานระบบ</div>'
            if forced else "")
    body = """%s%s<h1>เปลี่ยนรหัสผ่าน</h1>
<form method="post" action="/profile" class="card form narrow">%s %s %s
<div class="actions"><button class="btn ok" type="submit">บันทึกรหัสผ่านใหม่</button>
%s</div></form>""" % (
        note, err,
        field("รหัสผ่านเดิม", text("old_pwd", "", "", True, type_="password")),
        field("รหัสผ่านใหม่", text("new_pwd", "", "อย่างน้อย 6 ตัวอักษร", True, type_="password")),
        field("ยืนยันรหัสผ่านใหม่", text("new_pwd2", "", "", True, type_="password")),
        "" if forced else '<a class="btn ghost" href="/">ยกเลิก</a>')
    if forced:
        return """<!DOCTYPE html><html lang="th"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>เปลี่ยนรหัสผ่าน</title><link rel="stylesheet" href="/static/style.css"></head>
<body class="loginbg"><div class="loginwrap"><div class="loginbox wide">%s</div></div>
</body></html>""" % body
    return layout("เปลี่ยนรหัสผ่าน", body, "", user)


def page_dashboard(s, today, user):
    def card(t, v, cls="", link=""):
        k = '<div class="kpi %s"><b>%s</b><span>%s</span></div>' % (cls, v, esc(t))
        return '<a href="%s" class="kpi-link">%s</a>' % (link, k) if link else k

    def bars(data):
        mx = max([r["c"] for r in data] or [1])
        return "".join('<div class="bar"><span class="bl">%s</span>'
                       '<span class="bt"><i style="width:%d%%"></i></span>'
                       '<span class="bv">%d</span></div>'
                       % (esc(r["k"]), int(r["c"] * 100 / mx), r["c"]) for r in data) \
            or '<p class="muted">ยังไม่มีข้อมูล</p>'

    mx3 = max([r["c"] for r in s["last7"]] or [1])
    d7 = "".join('<div class="col"><i style="height:%d%%"></i><b>%d</b><span>%s</span></div>'
                 % (max(8, int(r["c"] * 100 / mx3)), r["c"], esc(r["k"][5:]))
                 for r in s["last7"]) or '<p class="muted">ยังไม่มีข้อมูล</p>'
    bu = "".join('<tr><td>%s</td><td class="num">%d</td></tr>' % (esc(r["k"]), r["c"])
                 for r in s["by_user"]) or '<tr><td colspan="2">ไม่มีข้อมูล</td></tr>'
    act = "".join(
        '<tr><td><b>%s</b></td><td>%s</td><td>%s</td><td class="muted">%s</td></tr>'
        % (esc(r["case_no"]), esc(r["detail"]), esc(r["actor"]), esc(r["at"][5:16]))
        for r in s["recent"]) or '<tr><td colspan="4" class="muted">ยังไม่มีความเคลื่อนไหว</td></tr>'

    empty = ""
    if s["total"] == 0:
        empty = ('<div class="alert ok">ยังไม่มีข้อมูลในระบบ — กด <b>เปิดงานใหม่</b> '
                 'หรือรัน <b>3_IMPORT_OLD_DATA.bat</b> บนเครื่อง Server</div>')
    hello = "สวัสดีค่ะ คุณ%s" % esc((user.get("full_name") or user["username"]).split()[0])

    return layout("หน้าหลัก", """%s
<h1>%s <small>%s &middot; ออนไลน์ %d คน</small></h1>
<section class="card mine"><h2>งานของฉัน</h2><div class="kpis sm">%s%s</div></section>
<div class="kpis">%s%s%s%s%s%s</div>
<div class="grid2">
 <section class="card"><h2>SLA เดือนนี้</h2><div class="kpis sm">%s%s</div></section>
 <section class="card"><h2>งานทั้งหมดในระบบ</h2><div class="kpis sm">%s</div></section>
</div>
<section class="card"><h2>ปริมาณงาน 7 วันล่าสุด</h2><div class="spark">%s</div></section>
<section class="card"><h2>ความเคลื่อนไหวล่าสุด</h2>
<div class="tablewrap"><table class="tbl"><thead><tr><th>Ticket</th><th>รายการ</th>
<th>โดย</th><th>เวลา</th></tr></thead><tbody>%s</tbody></table></div></section>
<div class="grid2">
 <section class="card"><h2>Top Category (เดือนนี้)</h2>%s</section>
 <section class="card"><h2>Top สาขาที่แจ้งมากสุด (เดือนนี้)</h2>%s</section>
</div>
<section class="card"><h2>งานแยกตามผู้ใช้ (เดือนนี้)</h2>
<table class="tbl"><thead><tr><th>ผู้ใช้</th><th class="num">จำนวน</th></tr></thead>
<tbody>%s</tbody></table></section>""" % (
        empty, hello, esc(today), s["users_online"],
        card("งานค้างของฉัน", s["mine_open"], "b3",
             "/tickets?created_by=%s&status=Pending" % esc(user["username"])),
        card("งานที่ฉันเปิดวันนี้", s["mine_today"], "b1",
             "/tickets?created_by=%s&date_from=%s&date_to=%s"
             % (esc(user["username"]), today, today)),
        card("งานวันนี้", s["today"], "b1", "/tickets?date_from=%s&date_to=%s" % (today, today)),
        card("งานเดือนนี้", s["month"], "b2", "/tickets?month=%s" % today[:7]),
        card("รอดำเนินการ", s["pending"], "b3", "/tickets?status=Pending"),
        card("กำลังตรวจสอบ", s["checking"], "b4", "/tickets?status=Checking"),
        card("แก้ไขแล้ว", s["resolved"], "b5", "/tickets?status=Resolved"),
        card("ปิดงานแล้ว", s["closed"], "b6", "/tickets?status=Close"),
        card("IN SLA", s["in_sla"], "b5"), card("OUT SLA", s["out_sla"], "b7"),
        card("ทั้งหมด", s["total"], "b2", "/tickets"),
        d7, act, bars(s["top_category"]), bars(s["top_branch"]), bu), "dash", user)


def _tabs(cur):
    items = [("", "ทั้งหมด"), ("Pending", "รอดำเนินการ"), ("Checking", "กำลังตรวจสอบ"),
             ("Resolved", "แก้ไขแล้ว"), ("Close", "ปิดงาน")]
    return "".join('<a class="tab %s" href="%s">%s</a>'
                   % ("on" if v == cur else "",
                      "/tickets?status=%s" % v if v else "/tickets", esc(t))
                   for v, t in items)


def page_tickets(rows, total, f, m, page, per_page, qs, user, users):
    mine = f.get("created_by", "")
    filt = """
<form class="filters card" method="get" action="/tickets">
 <div class="fgrid">%s %s %s %s %s %s %s %s</div>
 <div class="frow">
  <input type="search" name="q" value="%s" placeholder="ค้นหา: เลข Ticket / อาการ / สาขา / ผู้ติดต่อ">
  <button class="btn">ค้นหา</button>
  <a class="btn ghost" href="/tickets">ล้าง</a>
  <a class="btn ok" href="/export.csv?%s">ดาวน์โหลด CSV</a>
 </div></form>""" % (
        field("สถานะ", select("status", m["status"], f.get("status", ""), blank="ทั้งหมด")),
        field("ผู้เปิดงาน", select("created_by", users, mine, blank="ทุกคน")),
        field("Helpdesk", select("helpdesk", m["helpdesk"], f.get("helpdesk", ""), blank="ทั้งหมด")),
        field("Category", select("category", m["category"], f.get("category", ""), blank="ทั้งหมด")),
        field("Vendor", select("vendor", m["vendor"], f.get("vendor", ""), blank="ทั้งหมด")),
        field("Location", select("location", m["location"], f.get("location", ""), blank="ทั้งหมด")),
        field("ตั้งแต่วันที่", text("date_from", f.get("date_from", ""), type_="date")),
        field("ถึงวันที่", text("date_to", f.get("date_to", ""), type_="date")),
        esc(f.get("q", "")), esc(qs))

    tr = "".join("""<tr onclick="location='/tickets/%d'">
<td data-l="Ticket"><b>%s</b><br><small class="muted">%s %s</small></td>
<td data-l="สาขา">%s<br><small class="muted">%s %s</small></td>
<td data-l="อาการ"><div class="clip">%s</div></td>
<td data-l="ประเภท">%s<br><small class="muted">%s</small></td>
<td data-l="Vendor">%s</td><td data-l="ผู้เปิด">%s</td>
<td data-l="สถานะ">%s<br>%s</td></tr>"""
        % (r["id"], esc(r["case_no"]), esc(r["open_date"]), esc(r["open_time"]),
           esc(r["branch_name"]), esc(r["branch_code"]), esc(r["location"]),
           esc(r["problem_desc"]), esc(r["category"]), esc(r["ticket_type"]),
           esc(r["vendor_name"]), esc(r.get("created_by") or r.get("helpdesk") or "-"),
           badge(r["status"]), sla_badge(r["sla_result"])) for r in rows) \
        or '<tr><td colspan="7" class="muted" style="padding:24px">ไม่พบข้อมูลตามเงื่อนไข</td></tr>'

    pages = max(1, (total + per_page - 1) // per_page)
    pg = ""
    if pages > 1:
        base = "/tickets?%s&page=" % qs if qs else "/tickets?page="
        if page > 1:
            pg += '<a class="btn ghost" href="%s%d">&laquo; ก่อนหน้า</a>' % (base, page - 1)
        pg += '<span class="pginfo">หน้า %d / %d</span>' % (page, pages)
        if page < pages:
            pg += '<a class="btn ghost" href="%s%d">ถัดไป &raquo;</a>' % (base, page + 1)
    mybtn = ('<a class="tab %s" href="/tickets?created_by=%s">งานของฉัน</a>'
             % ("on" if mine == user["username"] else "", esc(user["username"])))

    return layout("รายการงาน", """<h1>รายการงาน <small>พบ %d รายการ</small></h1>%s
<div class="tabs">%s%s</div>
<div class="tablewrap"><table class="tbl rows"><thead><tr>
<th>Ticket</th><th>สาขา</th><th>อาการ</th><th>ประเภท</th><th>Vendor</th>
<th>ผู้เปิด</th><th>สถานะ</th></tr></thead><tbody>%s</tbody></table></div>
<div class="pager">%s</div>""" % (total, filt, _tabs(f.get("status", "")), mybtn, tr, pg),
                  "tickets", user)


def ticket_form(m, branches, user, t=None, error="", history=None):
    t = t or {}
    new = not t.get("id")
    ro = user.get("role") == "viewer"
    today = datetime.date.today().isoformat()
    now = datetime.datetime.now().strftime("%H:%M")
    bopts = "".join('<option value="%s">%s - %s</option>'
                    % (esc(b["code"]), esc(b["code"]), esc(b["name"])) for b in branches)
    bmap = json.dumps({b["code"]: [b["name"], b["location"], b.get("tel", "")]
                       for b in branches}, ensure_ascii=False)
    err = '<div class="alert">%s</div>' % esc(error) if error else ""
    action = "/tickets/new" if new else "/tickets/%d" % t["id"]

    meta = ""
    if not new:
        meta = ('<div class="metabar">เปิดโดย <b>%s</b> เมื่อ %s%s</div>'
                % (esc(t.get("created_by") or "-"), esc((t.get("created_at") or "")[:16]),
                   (' &middot; แก้ไขล่าสุดโดย <b>%s</b> เมื่อ %s'
                    % (esc(t.get("updated_by") or "-"), esc((t.get("updated_at") or "")[:16])))
                   if t.get("updated_by") else ""))
    hist = ""
    if history:
        rows = "".join('<tr><td>%s</td><td>%s</td><td class="muted">%s</td></tr>'
                       % (esc(h["detail"]), esc(h["actor"]), esc(h["at"][5:16]))
                       for h in history)
        hist = ('<section class="card"><h2>ประวัติการแก้ไข</h2>'
                '<div class="tablewrap"><table class="tbl"><thead><tr><th>รายการ</th>'
                '<th>โดย</th><th>เวลา</th></tr></thead><tbody>%s</tbody></table></div>'
                '</section>' % rows)
    if ro:
        btns = '<a class="btn ghost" href="/tickets">กลับรายการงาน</a>'
    else:
        btns = ('<button class="btn ok" type="submit">%s</button>'
                '<a class="btn ghost" href="/tickets">ยกเลิก</a>%s'
                % ("บันทึกเปิดงาน" if new else "บันทึกการแก้ไข",
                   "" if new or user.get("role") != "admin" else
                   ('<a class="btn danger" href="/tickets/%d/delete" '
                    'onclick="return confirm(\'ยืนยันลบงานนี้?\')">ลบงาน</a>' % t["id"])))

    body = """%s<h1>%s</h1>%s
<form method="post" action="%s" class="card form" id="tform"%s>
<fieldset><legend>1. ข้อมูลการแจ้ง</legend><div class="fgrid">%s %s %s %s %s %s</div></fieldset>
<fieldset><legend>2. สาขาและผู้ติดต่อ</legend><div class="fgrid">%s %s %s %s %s %s</div></fieldset>
<fieldset><legend>3. รายละเอียดปัญหา</legend>%s
<div class="fgrid">%s %s %s %s</div><div class="fgrid">%s %s %s %s %s</div></fieldset>
<fieldset><legend>4. การส่งต่อ / Vendor</legend><div class="fgrid">%s %s %s %s %s %s</div></fieldset>
<fieldset><legend>5. การปิดงานและ SLA</legend><div class="fgrid">%s %s %s %s %s %s</div>%s</fieldset>
<div class="actions">%s</div></form>%s
<datalist id="branchlist">%s</datalist>
<script>window.BRANCHES=%s;</script>""" % (
        err, "เปิดงานใหม่ (Ticket)" if new else "แก้ไขงาน %s" % esc(t.get("case_no", "")),
        meta, action, ' class="ro"' if ro else "",
        field("เลข Ticket *", text("case_no", t.get("case_no", ""), "เช่น CS0665478", True,
                                   attrs='autocomplete="off" %s' % ("" if new else "readonly")),
              "กรอกเลขงานจาก ServiceNow เอง"),
        field("วันที่แจ้ง *", text("open_date", t.get("open_date", today), type_="date", required=True)),
        field("เวลาแจ้ง *", text("open_time", (t.get("open_time") or now)[:5], type_="time", required=True)),
        field("Helpdesk *", select("helpdesk", m["helpdesk"],
                                   t.get("helpdesk", "") or user.get("full_name", ""), True)),
        field("Service Type", select("service_type", m["service_type"], t.get("service_type", ""))),
        field("สถานะ *", select("status", m["status"], t.get("status", "Pending"), True, blank=None)),
        field("รหัสสาขา *", text("branch_code", t.get("branch_code", ""), "เช่น 4127", True,
                                 attrs='list="branchlist" autocomplete="off" inputmode="numeric"'),
              "พิมพ์รหัสหรือเลือกจากรายการ ระบบเติมชื่อสาขาให้อัตโนมัติ"),
        field("ชื่อสาขา", text("branch_name", t.get("branch_name", ""))),
        field("Location", select("location", m["location"], t.get("location", ""))),
        field("ชื่อผู้ติดต่อ", text("contact_name", t.get("contact_name", ""))),
        field("ตำแหน่ง", select("job_title", m["job_title"], t.get("job_title", ""))),
        field("เบอร์ติดต่อ", text("phone_no", t.get("phone_no", ""), type_="tel")),
        field("อาการ / รายละเอียดปัญหา *",
              textarea("problem_desc", t.get("problem_desc", ""), 4, "อธิบายอาการที่สาขาแจ้ง")),
        field("Type", select("ticket_type", m["type"], t.get("ticket_type", ""))),
        field("Category", select("category", m["category"], t.get("category", ""))),
        field("อุปกรณ์ (Device)", select("device", m["device"], t.get("device", ""))),
        field("ชื่อโปรแกรม (Software)", text("software", t.get("software", ""))),
        field("Serial Number", text("serial_no", t.get("serial_no", ""))),
        field("Asset Tag", text("asset_tag", t.get("asset_tag", ""))),
        field("หมายเลข HHT", text("hht", t.get("hht", ""))),
        field("CID UIH (Network)", text("cid_uih", t.get("cid_uih", ""))),
        field("ยี่ห้อ / รุ่น", text("model", t.get("model", ""))),
        field("ส่งต่อให้", select("dispatch_to", m["dispatch"], t.get("dispatch_to", ""))),
        field("ชื่อ Vendor", select("vendor_name", m["vendor"], t.get("vendor_name", ""))),
        field("ผู้รับผิดชอบ", select("responsible", m["responsible"], t.get("responsible", ""))),
        field("Service Order", text("service_order", t.get("service_order", ""))),
        field("วันที่แจ้ง Vendor", text("vendor_date", t.get("vendor_date", ""), type_="date")),
        field("เวลาแจ้ง Vendor", text("vendor_time", (t.get("vendor_time") or "")[:5], type_="time")),
        field("วันที่แก้ไขเสร็จ", text("resolved_date", t.get("resolved_date", ""), type_="date")),
        field("เวลาแก้ไขเสร็จ", text("resolved_time", (t.get("resolved_time") or "")[:5], type_="time")),
        field("วันที่ปิดงาน", text("close_date", t.get("close_date", ""), type_="date")),
        field("เวลาปิดงาน", text("close_time", (t.get("close_time") or "")[:5], type_="time")),
        field("SLA (ชั่วโมง)", select("sla_hour", m["sla_hour"], t.get("sla_hour", ""))),
        field("ผลประเมิน SLA", select("sla_result", m["sla_result"],
                                      t.get("sla_result", "ยังไม่ประเมิน"), blank=None)),
        field("บันทึกเพิ่มเติม / การติดตาม",
              textarea("memo", t.get("memo", ""), 4, "บันทึกการติดตามงาน")),
        btns, hist, bopts, bmap)
    return layout("เปิดงานใหม่" if new else "แก้ไขงาน", body,
                  "new" if new else "tickets", user)


def page_reports(month, daily, groups, m, user):
    rows = "".join('<tr><td>%s</td><td class="num">%d</td><td class="num">%d</td>'
                   '<td class="num">%d</td><td class="num">%d</td><td class="num">%d</td></tr>'
                   % (esc(r["k"]), r["total"], r["pending"], r["resolved"],
                      r["closed"], r["out_sla"]) for r in daily)
    tot = sum(r["total"] for r in daily)
    if not rows:
        rows = '<tr><td colspan="6" class="muted">ไม่มีข้อมูลในเดือนนี้</td></tr>'

    def gtable(title, data):
        b = "".join('<tr><td>%s</td><td class="num">%d</td><td class="num">%.1f%%</td></tr>'
                    % (esc(r["k"] or "-"), r["c"], r["c"] * 100.0 / max(tot, 1))
                    for r in data) or '<tr><td colspan="3" class="muted">-</td></tr>'
        return ('<section class="card"><h2>%s</h2><table class="tbl"><thead><tr>'
                '<th>รายการ</th><th class="num">จำนวน</th><th class="num">สัดส่วน</th>'
                '</tr></thead><tbody>%s</tbody></table></section>' % (esc(title), b))

    return layout("รายงาน", """<h1>รายงาน</h1>
<form class="card filters" method="get" action="/reports"><div class="frow">%s
<button class="btn">แสดงรายงาน</button>
<a class="btn ok" href="/export.csv?month=%s">CSV รายเดือน</a>
<a class="btn ok" href="/export.csv?date_from=%s&date_to=%s">CSV วันนี้</a></div></form>
<section class="card"><h2>สรุปรายวัน — เดือน %s (รวม %d งาน)</h2>
<div class="tablewrap"><table class="tbl"><thead><tr><th>วันที่</th>
<th class="num">ทั้งหมด</th><th class="num">ค้าง</th><th class="num">แก้ไขแล้ว</th>
<th class="num">ปิดงาน</th><th class="num">OUT SLA</th></tr></thead>
<tbody>%s</tbody></table></div></section>
<div class="grid2">%s%s</div><div class="grid2">%s%s</div>""" % (
        field("เลือกเดือน", text("month", month, type_="month")), esc(month),
        datetime.date.today().isoformat(), datetime.date.today().isoformat(),
        esc(month), tot, rows,
        gtable("แยกตาม Category", groups["category"]),
        gtable("แยกตาม Vendor", groups["vendor"]),
        gtable("แยกตามผู้เปิดงาน", groups["user"]),
        gtable("แยกตามสาขา (Top 15)", groups["branch"][:15])), "reports", user)


def page_masters(m, bcount, user):
    labels = {"helpdesk": "เจ้าหน้าที่ Helpdesk", "service_type": "Service Type",
              "status": "สถานะงาน", "type": "Type", "location": "Location",
              "category": "Category", "device": "อุปกรณ์", "vendor": "Vendor",
              "responsible": "ผู้รับผิดชอบ", "dispatch": "ส่งต่อให้",
              "job_title": "ตำแหน่งผู้ติดต่อ", "sla_result": "ผล SLA",
              "sla_hour": "SLA (ชั่วโมง)"}
    admin = user.get("role") == "admin"
    blocks = ""
    for kind, items in m.items():
        chips = "".join(
            '<span class="chip">%s%s</span>'
            % (esc(i), ('<a href="/masters/del?kind=%s&value=%s" '
                        'onclick="return confirm(\'ลบ %s ?\')">&times;</a>'
                        % (esc(kind), esc(i), esc(i))) if admin else "")
            for i in items)
        form = ("""<form method="post" action="/masters/add" class="frow">
<input type="hidden" name="kind" value="%s">
<input name="value" placeholder="เพิ่มรายการใหม่..." required>
<button class="btn">เพิ่ม</button></form>""" % esc(kind)) if admin else ""
        blocks += ('<section class="card"><h2>%s <small class="muted">(%d รายการ)</small></h2>'
                   '<div class="chips">%s</div>%s</section>'
                   % (esc(labels.get(kind, kind)), len(items), chips, form))
    note = ""
    if bcount == 0:
        note = ('<div class="alert ok">ยังไม่มีข้อมูลสาขา — รัน '
                '<b>3_IMPORT_OLD_DATA.bat</b> บนเครื่อง Server</div>')
    if not admin:
        note += ('<div class="alert ok">คุณมีสิทธิ์ดูอย่างเดียว '
                 'การแก้ไขตัวเลือกต้องใช้บัญชีผู้ดูแลระบบ</div>')
    badd = ("""<section class="card"><h2>เพิ่มสาขาใหม่</h2>
<form method="post" action="/masters/branch" class="fgrid">%s %s %s %s
<div class="fld"><span>&nbsp;</span><button class="btn">เพิ่มสาขา</button></div>
</form></section>""" % (
        field("รหัสสาขา", text("code", "", "เช่น 4600", True)),
        field("ชื่อสาขา", text("name", "", "เช่น Central XXX", True)),
        field("Location", select("location", m["location"], "BKK", blank=None)),
        field("เบอร์โทรสาขา", text("tel", "", "เช่น 021234567")))) if admin else ""

    return layout("ตั้งค่า", """<h1>ตั้งค่าตัวเลือก (Master Data)</h1>%s
<p class="muted">สาขาในระบบ: <b>%d สาขา</b></p>%s%s"""
                  % (note, bcount, badd, blocks), "masters", user)


def page_users(users, user, error="", info=""):
    err = '<div class="alert">%s</div>' % esc(error) if error else ""
    inf = '<div class="alert ok">%s</div>' % esc(info) if info else ""
    rows = ""
    for u in users:
        st = ('<span class="badge st-resolved">ใช้งาน</span>' if u["active"]
              else '<span class="badge st-close">ปิดใช้งาน</span>')
        rows += ("""<tr>
<td data-l="ชื่อผู้ใช้"><b>%s</b></td><td data-l="ชื่อ-สกุล">%s</td>
<td data-l="สิทธิ์">%s</td><td data-l="เข้าล่าสุด" class="muted">%s</td>
<td data-l="สถานะ">%s</td><td data-l=""><a class="btn sm" href="/users/%d">แก้ไข</a></td></tr>"""
                 % (esc(u["username"]), esc(u["full_name"] or "-"),
                    esc(ROLE_TH.get(u["role"], u["role"])),
                    esc((u["last_login"] or "ยังไม่เคยเข้า")[:16]), st, u["id"]))

    form = """<section class="card"><h2>เพิ่มผู้ใช้ใหม่</h2>
<form method="post" action="/users/new" class="fgrid">%s %s %s %s %s
<div class="fld"><span>&nbsp;</span><button class="btn ok">สร้างบัญชี</button></div>
</form>
<p class="muted" style="margin-top:10px">ผู้ใช้ใหม่จะถูกบังคับให้เปลี่ยนรหัสผ่าน
เมื่อเข้าสู่ระบบครั้งแรก</p></section>""" % (
        field("ชื่อผู้ใช้ *", text("username", "", "เช่น sarita", True,
                                   attrs='autocapitalize="off"'), "ใช้ตอน Login ห้ามซ้ำ"),
        field("ชื่อ-นามสกุล *", text("full_name", "", "เช่น Sarita Hubsan", True)),
        field("รหัสผ่านเริ่มต้น *", text("password", "", "อย่างน้อย 6 ตัว", True)),
        field("สิทธิ์ *", select("role", ["staff", "admin", "viewer"], "staff", blank=None)),
        field("อีเมล", text("email", "", "ไม่บังคับ", type_="email")))

    return layout("ผู้ใช้งาน", """%s%s<h1>จัดการผู้ใช้งาน <small>%d บัญชี</small></h1>%s
<section class="card"><h2>รายชื่อผู้ใช้</h2>
<div class="tablewrap"><table class="tbl rows"><thead><tr>
<th>ชื่อผู้ใช้</th><th>ชื่อ-สกุล</th><th>สิทธิ์</th><th>เข้าล่าสุด</th>
<th>สถานะ</th><th></th></tr></thead><tbody>%s</tbody></table></div></section>
<section class="card"><h2>คำอธิบายสิทธิ์</h2>
<table class="tbl"><thead><tr><th>สิทธิ์</th><th>ทำอะไรได้</th></tr></thead><tbody>
<tr><td><b>ผู้ดูแลระบบ</b></td><td>ทุกอย่าง รวมถึงจัดการผู้ใช้ แก้ตัวเลือก และลบงาน</td></tr>
<tr><td><b>เจ้าหน้าที่ Helpdesk</b></td><td>เปิดงาน แก้ไขงาน ดูรายงาน ส่งออก CSV (ลบงานไม่ได้)</td></tr>
<tr><td><b>ดูอย่างเดียว</b></td><td>ดูข้อมูลและรายงานได้ แต่แก้ไขอะไรไม่ได้</td></tr>
</tbody></table></section>""" % (err, inf, len(users), form, rows), "users", user)


def page_user_edit(u, user, error="", info=""):
    err = '<div class="alert">%s</div>' % esc(error) if error else ""
    inf = '<div class="alert ok">%s</div>' % esc(info) if info else ""
    body = """%s%s<h1>แก้ไขผู้ใช้ <small>%s</small></h1>
<form method="post" action="/users/%d" class="card form">
<div class="fgrid">%s %s %s %s</div>
<div class="actions"><button class="btn ok" type="submit">บันทึก</button>
<a class="btn ghost" href="/users">กลับ</a></div></form>
<form method="post" action="/users/%d/pwd" class="card form">
<h2>รีเซ็ตรหัสผ่าน</h2><div class="fgrid">%s</div>
<div class="actions"><button class="btn" type="submit">ตั้งรหัสผ่านใหม่</button></div>
<p class="muted" style="margin-top:8px">ผู้ใช้จะถูกบังคับให้เปลี่ยนรหัสผ่านเองเมื่อ Login ครั้งถัดไป
และเซสชันเดิมทั้งหมดจะถูกตัดออก</p></form>""" % (
        err, inf, esc(u["username"]), u["id"],
        field("ชื่อ-นามสกุล", text("full_name", u["full_name"] or "")),
        field("สิทธิ์", select("role", ["staff", "admin", "viewer"], u["role"], blank=None)),
        field("อีเมล", text("email", u["email"] or "", type_="email")),
        field("สถานะ", select("active", ["ใช้งาน", "ปิดใช้งาน"],
                              "ใช้งาน" if u["active"] else "ปิดใช้งาน", blank=None)),
        u["id"],
        field("รหัสผ่านใหม่", text("password", "", "อย่างน้อย 6 ตัวอักษร", True)))
    return layout("แก้ไขผู้ใช้", body, "users", user)


def page_saved(case_no, tid, user):
    return layout("บันทึกสำเร็จ", """<div class="card center"><h1>บันทึกเรียบร้อย</h1>
<p class="big">Ticket <b>%s</b></p><div class="actions center">
<a class="btn ok" href="/tickets/new">เปิดงานใหม่อีกครั้ง</a>
<a class="btn" href="/tickets/%d">ดู / แก้ไขงานนี้</a>
<a class="btn ghost" href="/tickets">กลับรายการงาน</a></div></div>"""
                  % (esc(case_no), tid), "", user)


def page_denied(user):
    return layout("ไม่มีสิทธิ์", """<div class="card center">
<h1>ไม่มีสิทธิ์เข้าถึง</h1>
<p class="muted">บัญชีของคุณ (%s) ไม่มีสิทธิ์ใช้งานหน้านี้<br>
หากต้องการสิทธิ์เพิ่ม กรุณาติดต่อผู้ดูแลระบบ</p>
<div class="actions center"><a class="btn" href="/">กลับหน้าหลัก</a></div></div>"""
                  % esc(ROLE_TH.get(user.get("role"), "")), "", user)
