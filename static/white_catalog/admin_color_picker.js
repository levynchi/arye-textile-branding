(function () {
  "use strict";

  var STORAGE_KEY = "whiteColorSampledHex";
  // localStorage (not sessionStorage) so the related-object popup can read
  // a hex that was sampled on the product change page.

  function normalizeHex(value) {
    if (!value) return "";
    var raw = String(value).trim();
    if (!raw) return "";
    if (raw.charAt(0) !== "#") raw = "#" + raw;
    if (/^#[0-9a-fA-F]{3}$/.test(raw)) {
      raw =
        "#" +
        raw.charAt(1) +
        raw.charAt(1) +
        raw.charAt(2) +
        raw.charAt(2) +
        raw.charAt(3) +
        raw.charAt(3);
    }
    if (!/^#[0-9a-fA-F]{6}$/.test(raw)) return "";
    return raw.toLowerCase();
  }

  function rgbToHex(r, g, b) {
    function to2(n) {
      var h = Math.max(0, Math.min(255, n | 0)).toString(16);
      return h.length === 1 ? "0" + h : h;
    }
    return "#" + to2(r) + to2(g) + to2(b);
  }

  function setHex(input, hex) {
    var normalized = normalizeHex(hex);
    if (!normalized || !input) return;
    input.value = normalized;
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function enhanceHexField(hexInput) {
    if (!hexInput || hexInput.dataset.wcEnhanced === "1") return;
    hexInput.dataset.wcEnhanced = "1";

    var wrap = document.createElement("div");
    wrap.className = "wc-color-picker-wrap";

    var colorInput = document.createElement("input");
    colorInput.type = "color";
    colorInput.title = "בחר צבע";
    colorInput.value = normalizeHex(hexInput.value) || "#ffffff";

    var preview = document.createElement("span");
    preview.className = "wc-hex-preview";
    preview.style.background = normalizeHex(hexInput.value) || "transparent";

    var dropperBtn = document.createElement("button");
    dropperBtn.type = "button";
    dropperBtn.className = "button";
    dropperBtn.textContent = "דגום צבע מהמסך";

    var imageBtn = document.createElement("button");
    imageBtn.type = "button";
    imageBtn.className = "button";
    imageBtn.textContent = "דגום מתמונת דוגמית";

    wrap.appendChild(colorInput);
    wrap.appendChild(preview);
    wrap.appendChild(dropperBtn);
    wrap.appendChild(imageBtn);
    hexInput.parentNode.appendChild(wrap);

    function syncFromText() {
      var hex = normalizeHex(hexInput.value);
      if (hex) {
        colorInput.value = hex;
        preview.style.background = hex;
      }
    }

    hexInput.addEventListener("input", syncFromText);
    hexInput.addEventListener("change", syncFromText);

    colorInput.addEventListener("input", function () {
      setHex(hexInput, colorInput.value);
      preview.style.background = colorInput.value;
    });

    dropperBtn.addEventListener("click", function () {
      if (!window.EyeDropper) {
        window.alert("הדפדפן לא תומך בדגימת צבע מהמסך. השתמשו ב-Chrome / Edge.");
        return;
      }
      var eye = new window.EyeDropper();
      eye
        .open()
        .then(function (result) {
          setHex(hexInput, result.sRGBHex);
          preview.style.background = normalizeHex(result.sRGBHex);
        })
        .catch(function () {});
    });

    imageBtn.addEventListener("click", function () {
      var fileInput = document.getElementById("id_swatch_image");
      if (!fileInput || !fileInput.files || !fileInput.files[0]) {
        // Prefer currently saved image link if editing an existing color.
        var existing = document.querySelector(".field-swatch_image a");
        if (existing && existing.href) {
          openImageSampler(existing.href, function (hex) {
            setHex(hexInput, hex);
            preview.style.background = hex;
          });
          return;
        }
        window.alert("בחרו קודם תמונת דוגמית, או השתמשו ב״דגום צבע מהמסך״ על תמונת המוצר.");
        return;
      }
      var url = URL.createObjectURL(fileInput.files[0]);
      openImageSampler(url, function (hex) {
        setHex(hexInput, hex);
        preview.style.background = hex;
        URL.revokeObjectURL(url);
      });
    });

    // Prefill from product-page sampler (localStorage — shared with popup windows).
    try {
      var stored = normalizeHex(localStorage.getItem(STORAGE_KEY) || "");
      if (stored && !normalizeHex(hexInput.value)) {
        setHex(hexInput, stored);
        preview.style.background = stored;
        localStorage.removeItem(STORAGE_KEY);
      }
    } catch (e) {}

    syncFromText();
  }

  function openImageSampler(imageUrl, onPick) {
    var existing = document.getElementById("wc-sample-modal");
    if (existing) existing.remove();

    var modal = document.createElement("div");
    modal.id = "wc-sample-modal";
    modal.className = "wc-sample-modal is-open";
    modal.innerHTML =
      '<div class="wc-sample-dialog">' +
      "<h2>דגימת צבע מהתמונה</h2>" +
      "<p>לחצו על נקודה בתמונה כדי לדגום את הצבע</p>" +
      '<div class="wc-sample-canvas-wrap"><canvas></canvas></div>' +
      '<div class="wc-sample-toolbar">' +
      '<span class="wc-picked"><span class="wc-picked-swatch"></span><code class="wc-picked-hex">—</code></span>' +
      '<button type="button" class="button default wc-use-hex">השתמש בצבע זה</button>' +
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
      window.alert("לא ניתן לטעון את התמונה לדגימה. נסו ״דגום צבע מהמסך״.");
      modal.remove();
    };
    img.src = imageUrl;

    function sampleAt(clientX, clientY) {
      var rect = canvas.getBoundingClientRect();
      var x = Math.floor(((clientX - rect.left) / rect.width) * canvas.width);
      var y = Math.floor(((clientY - rect.top) / rect.height) * canvas.height);
      if (x < 0 || y < 0 || x >= canvas.width || y >= canvas.height) return;
      var data = ctx.getImageData(x, y, 1, 1).data;
      picked = rgbToHex(data[0], data[1], data[2]);
      swatch.style.background = picked;
      hexEl.textContent = picked;
    }

    canvas.addEventListener("click", function (e) {
      sampleAt(e.clientX, e.clientY);
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

  function init() {
    enhanceHexField(document.getElementById("id_hex_color"));
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
