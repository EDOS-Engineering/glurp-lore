// Page-turn keys: left and right arrows follow the page's rel=prev / rel=next links.
(function () {
  document.addEventListener("keydown", function (e) {
    if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
    var t = e.target;
    if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;
    var rel = e.key === "ArrowLeft" ? "prev" : "next";
    var link = document.querySelector('a[rel="' + rel + '"]') || document.querySelector('link[rel="' + rel + '"]');
    if (link) window.location.href = link.getAttribute("href");
  });
})();
