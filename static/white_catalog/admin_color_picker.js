(function () {
  "use strict";

  var STORAGE_KEY = "whiteColorSampledHex";
  // localStorage (not sessionStorage) so the related-object popup can read
  // a hex that was sampled on the product change page.
  var MIN_DRAG_PX = 8;
  var MAX_CROP_EDGE = 640;

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

  function averageHexFromCanvas(source) {
    var sctx = source.getContext("2d", { willReadFrequently: true });
    var w = source.width;
    var h = source.height;
    if (!w || !h) return "";
    var data;
    try {
      data = sctx.getImageData(0, 0, w, h).data;
    } catch (err) {
      return "";
    }
    var step = Math.max(1, Math.floor(Math.sqrt((w * h) / 4000)));
    var r = 0;
    var g = 0;
    var b = 0;
    var n = 0;
    var rowStride = w * 4;
    var py;
    var px;
    for (py = 0; py < h; py += step) {
      for (px = 0; px < w; px += step) {
        var i = py * rowStride + px * 4;
        if (data[i + 3] < 16) continue;
        r += data[i];
        g += data[i + 1];
        b += data[i + 2];
        n++;
      }
    }
    if (!n) return "";
    return rgbToHex(Math.round(r / n), Math.round(g / n), Math.round(b / n));
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
    imageBtn.textContent = "ערוך תמונת דוגמית";

    wrap.appendChild(colorInput);
    wrap.appendChild(preview);
    wrap.appendChild(dropperBtn);
    wrap.appendChild(imageBtn);
    hexInput.parentNode.appendChild(wrap);

    function showFlatPreview(hex) {
      if (preview._wcUrl) {
        URL.revokeObjectURL(preview._wcUrl);
        preview._wcUrl = "";
      }
      preview.style.backgroundImage = "";
      preview.style.backgroundSize = "";
      preview.style.backgroundPosition = "";
      preview.style.background = hex || "transparent";
    }

    function showCropPreview(file) {
      if (preview._wcUrl) URL.revokeObjectURL(preview._wcUrl);
      var url = URL.createObjectURL(file);
      preview._wcUrl = url;
      preview.style.backgroundColor = "transparent";
      preview.style.backgroundImage = 'url("' + url + '")';
      preview.style.backgroundSize = "cover";
      preview.style.backgroundPosition = "center";
    }

    function showFilePreview(file) {
      var fileInput = document.getElementById("id_swatch_image");
      if (!fileInput || !fileInput.parentNode) return;
      var imgEl = fileInput.parentNode.querySelector(".wc-swatch-file-preview");
      if (!imgEl) {
        imgEl = document.createElement("img");
        imgEl.className = "wc-swatch-file-preview";
        imgEl.alt = "האזור שיישמר כדוגמית";
        fileInput.parentNode.appendChild(imgEl);
      }
      if (imgEl._wcUrl) URL.revokeObjectURL(imgEl._wcUrl);
      var url = URL.createObjectURL(file);
      imgEl._wcUrl = url;
      imgEl.src = url;
    }

    function assignSwatchFile(file) {
      var fileInput = document.getElementById("id_swatch_image");
      if (!fileInput || typeof DataTransfer === "undefined") {
        window.alert("הדפדפן לא מאפשר להכניס את החיתוך לשדה התמונה. השתמשו ב-Chrome / Edge.");
        return false;
      }
      var transfer = new DataTransfer();
      transfer.items.add(file);
      fileInput.files = transfer.files;
      fileInput.dispatchEvent(new Event("change", { bubbles: true }));
      var clearBox = document.querySelector('.field-swatch_image input[type="checkbox"]');
      if (clearBox) clearBox.checked = false;
      showFilePreview(file);
      return true;
    }

    function applyPick(result) {
      if (!result || !result.hex) return;
      setHex(hexInput, result.hex);
      colorInput.value = normalizeHex(result.hex) || colorInput.value;
      if (result.file) {
        if (assignSwatchFile(result.file)) showCropPreview(result.file);
        return;
      }
      showFlatPreview(result.hex);
    }

    function syncFromText() {
      var hex = normalizeHex(hexInput.value);
      if (!hex || preview._wcUrl) return;
      colorInput.value = hex;
      preview.style.background = hex;
    }

    hexInput.addEventListener("input", syncFromText);
    hexInput.addEventListener("change", syncFromText);

    colorInput.addEventListener("input", function () {
      setHex(hexInput, colorInput.value);
      showFlatPreview(colorInput.value);
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
          var hex = normalizeHex(result.sRGBHex);
          setHex(hexInput, hex);
          colorInput.value = hex || colorInput.value;
          showFlatPreview(hex);
        })
        .catch(function () {});
    });

    imageBtn.addEventListener("click", function () {
      var fileInput = document.getElementById("id_swatch_image");
      if (!fileInput || !fileInput.files || !fileInput.files[0]) {
        // Prefer currently saved image link if editing an existing color.
        var existing = document.querySelector(".field-swatch_image a");
        if (existing && existing.href) {
          openImageSampler(existing.href, applyPick);
          return;
        }
        window.alert("בחרו קודם תמונת דוגמית, או השתמשו ב״דגום צבע מהמסך״ על תמונת המוצר.");
        return;
      }
      var url = URL.createObjectURL(fileInput.files[0]);
      openImageSampler(url, applyPick);
    });

    // Prefill from product-page sampler (localStorage — shared with popup windows).
    try {
      var stored = normalizeHex(localStorage.getItem(STORAGE_KEY) || "");
      if (stored && !normalizeHex(hexInput.value)) {
        setHex(hexInput, stored);
        showFlatPreview(stored);
        localStorage.removeItem(STORAGE_KEY);
      }
    } catch (e) {}

    syncFromText();
  }

  var SWATCH_PX = 104;

  function openImageSampler(imageUrl, onPick) {
    var existing = document.getElementById("wc-sample-modal");
    if (existing) {
      if (existing._wcRelease) existing._wcRelease();
      existing.remove();
    }

    var modal = document.createElement("div");
    modal.id = "wc-sample-modal";
    modal.className = "wc-sample-modal is-open";
    modal.innerHTML =
      '<div class="wc-sample-dialog">' +
      "<h2>עריכת דוגמית</h2>" +
      "<p>גררו את התמונה מתחת לעיגול, וגלגלו כדי להגדיל או להקטין. העיגול הוא בדיוק מה שהלקוח יראה. לחיצה על נקודה דוגמת רק את קוד הצבע.</p>" +
      '<div class="wc-sample-layout">' +
      '<div class="wc-sample-stage"><canvas></canvas><div class="wc-sample-circle"></div></div>' +
      '<div class="wc-sample-live"><div class="wc-customer-preview"></div><span>כך הלקוח יראה</span></div>' +
      "</div>" +
      '<div class="wc-sample-toolbar">' +
      '<span class="wc-picked"><span class="wc-picked-swatch"></span><code class="wc-picked-hex">—</code></span>' +
      '<button type="button" class="button default wc-use-hex">השתמש באזור זה</button>' +
      '<button type="button" class="button wc-close-modal">סגור</button>' +
      "</div></div>";

    document.body.appendChild(modal);

    var stage = modal.querySelector(".wc-sample-stage");
    var canvas = modal.querySelector("canvas");
    var ctx = canvas.getContext("2d", { willReadFrequently: true });
    var preview = modal.querySelector(".wc-customer-preview");
    var swatch = modal.querySelector(".wc-picked-swatch");
    var hexEl = modal.querySelector(".wc-picked-hex");
    var useBtn = modal.querySelector(".wc-use-hex");
    var picked = "";
    var mode = "region";
    var centerX = 0;
    var centerY = 0;
    var span = SWATCH_PX;
    var drag = null;
    var ready = false;
    var closed = false;
    var previewUrl = "";

    var img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = function () {
      centerX = img.naturalWidth / 2;
      centerY = img.naturalHeight / 2;
      span = Math.min(img.naturalWidth, img.naturalHeight);
      ready = true;
      draw();
    };
    img.onerror = function () {
      window.alert("לא ניתן לטעון את התמונה לדגימה. נסו ״דגום צבע מהמסך״.");
      closeModal();
    };
    img.src = imageUrl;

    function releaseImageUrl() {
      if (imageUrl && imageUrl.indexOf("blob:") === 0) {
        URL.revokeObjectURL(imageUrl);
        imageUrl = "";
      }
      if (previewUrl && previewUrl.indexOf("blob:") === 0) URL.revokeObjectURL(previewUrl);
    }
    modal._wcRelease = releaseImageUrl;

    function closeModal() {
      if (closed) return;
      closed = true;
      releaseImageUrl();
      modal.remove();
    }

    function clampView() {
      var minSpan = Math.min(32, img.naturalWidth, img.naturalHeight);
      var maxSpan = Math.min(img.naturalWidth, img.naturalHeight);
      if (span < minSpan) span = minSpan;
      if (span > maxSpan) span = maxSpan;
      var half = span / 2;
      if (span >= img.naturalWidth) centerX = img.naturalWidth / 2;
      else {
        if (centerX < half) centerX = half;
        if (centerX > img.naturalWidth - half) centerX = img.naturalWidth - half;
      }
      if (span >= img.naturalHeight) centerY = img.naturalHeight / 2;
      else {
        if (centerY < half) centerY = half;
        if (centerY > img.naturalHeight - half) centerY = img.naturalHeight - half;
      }
    }

    function buildSquare() {
      clampView();
      var out = Math.max(SWATCH_PX, Math.min(MAX_CROP_EDGE, Math.round(span)));
      var crop = document.createElement("canvas");
      crop.width = out;
      crop.height = out;
      crop.getContext("2d").drawImage(
        img,
        centerX - span / 2,
        centerY - span / 2,
        span,
        span,
        0,
        0,
        out,
        out
      );
      return crop;
    }

    function showRegion() {
      var crop;
      try {
        crop = buildSquare();
      } catch (err) {
        return null;
      }
      var hex = averageHexFromCanvas(crop) || picked;
      var url;
      try {
        url = crop.toDataURL("image/jpeg", 0.85);
      } catch (err) {
        return null;
      }
      mode = "region";
      picked = hex;
      preview.style.backgroundImage = 'url("' + url + '")';
      preview.style.backgroundColor = "transparent";
      swatch.classList.add("is-crop");
      swatch.style.background = "transparent";
      swatch.style.backgroundImage = 'url("' + url + '")';
      swatch.style.backgroundSize = "cover";
      swatch.style.backgroundPosition = "center";
      hexEl.textContent = hex || "—";
      useBtn.textContent = "השתמש באזור זה";
      return crop;
    }

    function draw() {
      if (!ready) return;
      var width = stage.clientWidth || 640;
      var height = stage.clientHeight || 360;
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
      }
      clampView();
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      var pxPerNat = SWATCH_PX / span;
      var dx = canvas.width / 2 - centerX * pxPerNat;
      var dy = canvas.height / 2 - centerY * pxPerNat;
      ctx.drawImage(img, dx, dy, img.naturalWidth * pxPerNat, img.naturalHeight * pxPerNat);
      if (mode === "region") showRegion();
    }

    function showFlat(hex) {
      mode = "point";
      picked = hex;
      preview.style.backgroundImage = "";
      preview.style.backgroundColor = hex;
      swatch.classList.remove("is-crop");
      swatch.style.backgroundImage = "";
      swatch.style.backgroundSize = "";
      swatch.style.backgroundPosition = "";
      swatch.style.background = hex;
      hexEl.textContent = hex;
      useBtn.textContent = "השתמש בצבע זה";
    }

    function samplePoint(clientX, clientY) {
      var rect = canvas.getBoundingClientRect();
      var x = Math.round(((clientX - rect.left) * canvas.width) / rect.width);
      var y = Math.round(((clientY - rect.top) * canvas.height) / rect.height);
      if (x < 0 || y < 0 || x >= canvas.width || y >= canvas.height) return;
      var data;
      try {
        data = ctx.getImageData(x, y, 1, 1).data;
      } catch (err) {
        window.alert("לא ניתן לקרוא את הצבע מהתמונה. העלו את הקובץ מחדש, או השתמשו ב״דגום צבע מהמסך״.");
        return;
      }
      if (data[3] < 16) return;
      showFlat(rgbToHex(data[0], data[1], data[2]));
    }

    stage.addEventListener("pointerdown", function (e) {
      if (!ready || e.button !== 0) return;
      drag = {
        x: e.clientX,
        y: e.clientY,
        centerX: centerX,
        centerY: centerY,
        pointerId: e.pointerId,
        moved: false,
      };
      stage.classList.add("is-dragging");
      try {
        stage.setPointerCapture(e.pointerId);
      } catch (err) {}
      e.preventDefault();
    });

    stage.addEventListener("pointermove", function (e) {
      if (!drag || e.pointerId !== drag.pointerId) return;
      var dx = e.clientX - drag.x;
      var dy = e.clientY - drag.y;
      if (Math.abs(dx) >= MIN_DRAG_PX || Math.abs(dy) >= MIN_DRAG_PX) drag.moved = true;
      if (!drag.moved) return;
      mode = "region";
      centerX = drag.centerX - dx * (span / SWATCH_PX);
      centerY = drag.centerY - dy * (span / SWATCH_PX);
      draw();
    });

    function finishDrag(e) {
      if (!drag || e.pointerId !== drag.pointerId) return;
      var moved = drag.moved;
      drag = null;
      stage.classList.remove("is-dragging");
      if (!moved) samplePoint(e.clientX, e.clientY);
    }

    stage.addEventListener("pointerup", finishDrag);
    stage.addEventListener("pointercancel", function (e) {
      if (!drag || e.pointerId !== drag.pointerId) return;
      drag = null;
      stage.classList.remove("is-dragging");
    });

    stage.addEventListener(
      "wheel",
      function (e) {
        if (!ready) return;
        e.preventDefault();
        var factor = e.deltaY < 0 ? 0.9 : 1.1;
        span *= factor;
        mode = "region";
        draw();
      },
      { passive: false }
    );

    modal.querySelector(".wc-close-modal").addEventListener("click", closeModal);
    modal.addEventListener("click", function (e) {
      if (e.target === modal) closeModal();
    });
    useBtn.addEventListener("click", function () {
      if (mode === "region") {
        var crop = buildSquare();
        if (!crop) {
          window.alert("לא ניתן לשמור את האזור מהתמונה.");
          return;
        }
        var hex = averageHexFromCanvas(crop) || picked;
        useBtn.disabled = true;
        crop.toBlob(
          function (blob) {
            useBtn.disabled = false;
            if (!blob) {
              window.alert("לא ניתן לשמור את האזור מהתמונה.");
              return;
            }
            var file = new File([blob], "swatch-crop.jpg", { type: "image/jpeg" });
            onPick({ hex: hex, file: file });
            closeModal();
          },
          "image/jpeg",
          0.92
        );
        return;
      }
      if (!picked) {
        window.alert("לחצו על נקודה בתמונה, או גררו את התמונה בתוך העיגול");
        return;
      }
      onPick({ hex: picked, file: null });
      closeModal();
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
