(function () {
  var code = document.getElementById('branch_code');
  if (code && window.BRANCHES) {
    var fill = function () {
      var b = window.BRANCHES[(code.value || '').trim()];
      if (!b) return;
      var n = document.getElementById('branch_name'),
          l = document.getElementById('location'),
          p = document.getElementById('phone_no');
      if (n) n.value = b[0];
      if (l) l.value = b[1];
      if (p && !p.value) p.value = b[2] || '';
    };
    code.addEventListener('change', fill);
    code.addEventListener('blur', fill);
    code.addEventListener('input', function () {
      if ((code.value || '').length >= 4) fill();
    });
  }
  var st = document.getElementById('status');
  if (st) {
    st.addEventListener('change', function () {
      var d = new Date();
      var ds = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' +
               String(d.getDate()).padStart(2, '0');
      var ts = String(d.getHours()).padStart(2, '0') + ':' +
               String(d.getMinutes()).padStart(2, '0');
      var set = function (a, b) {
        var x = document.getElementById(a), y = document.getElementById(b);
        if (x && !x.value) x.value = ds;
        if (y && !y.value) y.value = ts;
      };
      if (st.value === 'Resolved') set('resolved_date', 'resolved_time');
      if (st.value === 'Close') { set('resolved_date','resolved_time'); set('close_date','close_time'); }
    });
  }
  var f = document.getElementById('tform');
  if (f && !f.classList.contains('ro')) f.addEventListener('submit', function () {
    var b = f.querySelector('button[type=submit]');
    if (b) { b.disabled = true; b.textContent = 'กำลังบันทึก...'; }
    setTimeout(function () { if (b) { b.disabled = false; } }, 5000);
  });
})();
