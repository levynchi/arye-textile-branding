(function () {
  "use strict";

  // localStorage so the related-object popup (new window) can read the sampled hex.
  var STORAGE_KEY = "whiteColorSampledHex";

  function rgbToHex(r, g, b) {
    function to2(n) {
      var h = Math.max(0, Math.min(255, n | 0)).toString(16);
      return h.length === 1 ? "0" + h : h;
    }
    return "#" + to2(r) + to2(g) + to2(b);
  }

  function findProductImageUrl() {
    var field = document.querySelector(".field-image");
    if (!field) return "";
    var link = field.querySelector("a[href]");
    if (link && /\.(png|jpe?g|webp|gif|bmp)(\?|$)/i.test(link.href)) {
      return link.href;
    }
    var img = field.querySelector("img");
    if (img && img.src) return img.src;
    return "";
  }

  function openImageSampler(imageUrl, onPick) {
    var existing = document.getElementById("wc-sample-modal");
    if (existing) existing.remove();

    var modal = document.createElement("div");
    modal.id = "wc-sample-modal";
    modal.className = "wc-sample-modal is-open";
    modal.innerHTML =
      '<div class="wc-sample-dialog">' +
      "<h2>דגימת צבע מתמונת המוצר</h2>" +
      "<p>לחצו על נקודה בתמונה. אחר כך לחצו + ליד שדה הצבע והקוד יוזן אוטומטית.</p>" +
      '<div class="wc-sample-canvas-wrap"><canvas></canvas></div>' +
      '<div class="wc-sample-toolbar">' +
      '<span class="wc-picked"><span class="wc-picked-swatch"></span><code class="wc-picked-hex">—</code></span>' +
      '<button type="button" class="button default wc-use-hex">שמור לדגימה הבאה</button>' +
      '<button type="button" class="button wc-close-modal">סגור</button>' +
      "</div></div>";

    document.body.appendChild(modal);

    var canvas = modal.querySelector("canvas");
    var ctx = canvas.getContext("2d", { willReadFrequently: true });
    var swatch = modal.querySelector(".wc-picked-swatch");
    var hexEl = modal.querySelector(".wc-picked-hex");
    var useBtn = modal.querySelector(".wc-use-hex");
    var picked = "";

    var img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = function () {
      var maxW = Math.min(860, window.innerWidth - 80);
      var scale = Math.min(1, maxW / img.naturalWidth);
      canvas.width = Math.round(img.naturalWidth * scale);
      canvas.height = Math.round(img.naturalHeight * scale);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    };
    img.onerror = function () {
      window.alert("לא ניתן לטעון את תמונת המוצר. נסו ״דגום מהמסך״ בחלון הוספת הצבע.");
      modal.remove();
    };
    img.src = imageUrl;

    canvas.addEventListener("click", function (e) {
      var rect = canvas.getBoundingClientRect();
      var x = Math.floor(((e.clientX - rect.left) / rect.width) * canvas.width);
      var y = Math.floor(((e.clientY - rect.top) / rect.height) * canvas.height);
      if (x < 0 || y < 0 || x >= canvas.width || y >= canvas.height) return;
      var data = ctx.getImageData(x, y, 1, 1).data;
      picked = rgbToHex(data[0], data[1], data[2]);
      swatch.style.background = picked;
      hexEl.textContent = picked;
    });

    modal.querySelector(".wc-close-modal").addEventListener("click", function () {
      modal.remove();
    });
    modal.addEventListener("click", function (e) {
      if (e.target === modal) modal.remove();
    });
    useBtn.addEventListener("click", function () {
      if (!picked) {
        window.alert("לחצו קודם על נקודה בתמונה");
        return;
      }
      onPick(picked);
      modal.remove();
    });
  }

  function insertToolbar() {
    var inlineGroup = document.getElementById("color_variants-group");
    if (!inlineGroup || inlineGroup.dataset.wcSampleBar === "1") return;
    inlineGroup.dataset.wcSampleBar = "1";

    var bar = document.createElement("div");
    bar.className = "wc-inline-sample-bar";
    bar.innerHTML =
      "<strong>דגימת צבע:</strong>" +
      '<button type="button" class="button wc-sample-product-btn">דגום מתמונת המוצר</button>' +
      '<button type="button" class="button wc-sample-screen-btn">דגום מהמסך</button>' +
      '<span class="wc-sample-status" style="color:#555;"></span>';

    var h2 = inlineGroup.querySelector("h2");
    if (h2 && h2.nextSibling) {
      inlineGroup.insertBefore(bar, h2.nextSibling);
    } else {
      inlineGroup.insertBefore(bar, inlineGroup.firstChild);
    }

    var status = bar.querySelector(".wc-sample-status");

    function remember(hex) {
      try {
        localStorage.setItem(STORAGE_KEY, hex);
      } catch (e) {}
      status.innerHTML =
        'נשמר <code style="font-weight:700;">' +
        hex +
        "</code> — עכשיו לחצו <strong>+</strong> ליד שדה הצבע, הזינו שם (למשל שמנת) ושמרו.";
    }

    bar.querySelector(".wc-sample-product-btn").addEventListener("click", function () {
      var url = findProductImageUrl();
      if (!url) {
        window.alert("לא נמצאה תמונה ראשית למוצר. העלו תמונה בשדה ״תמונה ראשית״ ושמרו, ואז דגמו.");
        return;
      }
      openImageSampler(url, remember);
    });

    bar.querySelector(".wc-sample-screen-btn").addEventListener("click", function () {
      if (!window.EyeDropper) {
        window.alert("הדפדפן לא תומך בדגימת צבע מהמסך. השתמשו ב-Chrome / Edge.");
        return;
      }
      var eye = new window.EyeDropper();
      eye
        .open()
        .then(function (result) {
          var hex = String(result.sRGBHex || "").toLowerCase();
          if (hex) remember(hex);
        })
        .catch(function () {});
    });
  }

  function init() {
    insertToolbar();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
