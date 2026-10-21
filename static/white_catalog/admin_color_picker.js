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
    imageBtn.textContent = "דגום מתמונת דוגמית";

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
      "<h2>דגימת צבע מהתמונה</h2>" +
      "<p>גררו מלבן על הבד. האזור שתסמנו יישמר כדוגמית שמוצגת בקטלוג. לחיצה על נקודה דוגמת רק את קוד הצבע.</p>" +
      '<div class="wc-sample-canvas-wrap"><canvas></canvas><div class="wc-sample-selection" hidden></div></div>' +
      '<div class="wc-sample-toolbar">' +
      '<span class="wc-picked"><span class="wc-picked-swatch"></span><code class="wc-picked-hex">—</code></span>' +
      '<button type="button" class="button default wc-use-hex">השתמש בצבע זה</button>' +
      '<button type="button" class="button wc-close-modal">סגור</button>' +
      "</div></div>";

    document.body.appendChild(modal);

    var canvas = modal.querySelector("canvas");
    var wrap = modal.querySelector(".wc-sample-canvas-wrap");
    var box = modal.querySelector(".wc-sample-selection");
    var ctx = canvas.getContext("2d", { willReadFrequently: true });
    var swatch = modal.querySelector(".wc-picked-swatch");
    var hexEl = modal.querySelector(".wc-picked-hex");
    var useBtn = modal.querySelector(".wc-use-hex");
    var picked = "";
    var mode = "";
    var cropCanvas = null;
    var drag = null;
    var ready = false;
    var closed = false;

    var img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = function () {
      var maxW = Math.min(860, window.innerWidth - 80);
      var scale = Math.min(1, maxW / img.naturalWidth);
      canvas.width = Math.round(img.naturalWidth * scale);
      canvas.height = Math.round(img.naturalHeight * scale);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      ready = true;
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
    }
    modal._wcRelease = releaseImageUrl;

    function closeModal() {
      if (closed) return;
      closed = true;
      releaseImageUrl();
      modal.remove();
    }

    function displayPoint(clientX, clientY) {
      var rect = canvas.getBoundingClientRect();
      var x = clientX - rect.left;
      var y = clientY - rect.top;
      if (x < 0) x = 0;
      if (y < 0) y = 0;
      if (x > rect.width) x = rect.width;
      if (y > rect.height) y = rect.height;
      return { x: x, y: y, rect: rect };
    }

    function placeBox(dispX, dispY, dispW, dispH) {
      var canvasRect = canvas.getBoundingClientRect();
      var wrapRect = wrap.getBoundingClientRect();
      box.style.left = canvasRect.left - wrapRect.left - wrap.clientLeft + dispX + "px";
      box.style.top = canvasRect.top - wrapRect.top - wrap.clientTop + dispY + "px";
      box.style.width = Math.max(0, dispW) + "px";
      box.style.height = Math.max(0, dispH) + "px";
      box.hidden = false;
    }

    function hideBox() {
      box.hidden = true;
    }

    function toCanvasRect(dx, dy, dw, dh, rect) {
      var sx = canvas.width / rect.width;
      var sy = canvas.height / rect.height;
      var x = Math.round(dx * sx);
      var y = Math.round(dy * sy);
      var w = Math.round(dw * sx);
      var h = Math.round(dh * sy);
      if (x < 0) x = 0;
      if (y < 0) y = 0;
      if (x + w > canvas.width) w = canvas.width - x;
      if (y + h > canvas.height) h = canvas.height - y;
      if (w < 1) w = 1;
      if (h < 1) h = 1;
      return { x: x, y: y, w: w, h: h };
    }

    function buildCrop(canvasRect) {
      var naturalW = img.naturalWidth || canvas.width;
      var naturalH = img.naturalHeight || canvas.height;
      var nx = naturalW / canvas.width;
      var ny = naturalH / canvas.height;
      var sx = canvasRect.x * nx;
      var sy = canvasRect.y * ny;
      var sw = canvasRect.w * nx;
      var sh = canvasRect.h * ny;
      var scale = Math.min(1, MAX_CROP_EDGE / Math.max(sw, sh));
      var outW = Math.max(1, Math.round(sw * scale));
      var outH = Math.max(1, Math.round(sh * scale));
      var crop = document.createElement("canvas");
      crop.width = outW;
      crop.height = outH;
      crop.getContext("2d").drawImage(img, sx, sy, sw, sh, 0, 0, outW, outH);
      return crop;
    }

    function showFlat(hex) {
      mode = "point";
      cropCanvas = null;
      picked = hex;
      swatch.classList.remove("is-crop");
      swatch.style.backgroundImage = "";
      swatch.style.backgroundSize = "";
      swatch.style.backgroundPosition = "";
      swatch.style.background = hex;
      hexEl.textContent = hex;
      useBtn.textContent = "השתמש בצבע זה";
      hideBox();
    }

    function showRegion(hex, crop) {
      var previewUrl;
      try {
        previewUrl = crop.toDataURL("image/jpeg", 0.85);
      } catch (err) {
        window.alert("לא ניתן להציג את האזור שסומן. העלו את הקובץ מחדש, או השתמשו ב״דגום צבע מהמסך״.");
        return false;
      }
      mode = "region";
      cropCanvas = crop;
      picked = hex;
      swatch.classList.add("is-crop");
      swatch.style.background = "transparent";
      swatch.style.backgroundImage = 'url("' + previewUrl + '")';
      swatch.style.backgroundSize = "cover";
      swatch.style.backgroundPosition = "center";
      hexEl.textContent = hex;
      useBtn.textContent = "השתמש באזור זה";
      return true;
    }

    function samplePoint(clientX, clientY) {
      var point = displayPoint(clientX, clientY);
      var mapped = toCanvasRect(point.x, point.y, 1, 1, point.rect);
      var data;
      try {
        data = ctx.getImageData(mapped.x, mapped.y, 1, 1).data;
      } catch (err) {
        window.alert("לא ניתן לקרוא את הצבע מהתמונה. העלו את הקובץ מחדש, או השתמשו ב״דגום צבע מהמסך״.");
        return;
      }
      showFlat(rgbToHex(data[0], data[1], data[2]));
    }

    function selectRegion(dispX, dispY, dispW, dispH, rect) {
      var mapped = toCanvasRect(dispX, dispY, dispW, dispH, rect);
      var crop;
      try {
        crop = buildCrop(mapped);
      } catch (err) {
        window.alert("לא ניתן לחתוך את האזור מהתמונה. העלו את הקובץ מחדש, או השתמשו ב״דגום צבע מהמסך״.");
        return;
      }
      var hex = averageHexFromCanvas(crop);
      if (!hex) {
        window.alert("לא ניתן לקרוא את הצבע מהאזור שסומן. העלו את הקובץ מחדש, או השתמשו ב״דגום צבע מהמסך״.");
        return;
      }
      if (!showRegion(hex, crop)) return;
      placeBox(dispX, dispY, dispW, dispH);
    }

    canvas.addEventListener("pointerdown", function (e) {
      if (!ready || e.button !== 0) return;
      var point = displayPoint(e.clientX, e.clientY);
      drag = {
        x0: point.x,
        y0: point.y,
        x1: point.x,
        y1: point.y,
        pointerId: e.pointerId,
        rect: point.rect,
      };
      try {
        canvas.setPointerCapture(e.pointerId);
      } catch (err) {}
      e.preventDefault();
    });

    canvas.addEventListener("pointermove", function (e) {
      if (!drag || e.pointerId !== drag.pointerId) return;
      var point = displayPoint(e.clientX, e.clientY);
      drag.x1 = point.x;
      drag.y1 = point.y;
      drag.rect = point.rect;
      placeBox(
        Math.min(drag.x0, drag.x1),
        Math.min(drag.y0, drag.y1),
        Math.abs(drag.x1 - drag.x0),
        Math.abs(drag.y1 - drag.y0)
      );
    });

    function finishDrag(e) {
      if (!drag || e.pointerId !== drag.pointerId) return;
      var start = drag;
      drag = null;
      var x = Math.min(start.x0, start.x1);
      var y = Math.min(start.y0, start.y1);
      var w = Math.abs(start.x1 - start.x0);
      var h = Math.abs(start.y1 - start.y0);
      if (w < MIN_DRAG_PX && h < MIN_DRAG_PX) {
        samplePoint(e.clientX, e.clientY);
        return;
      }
      selectRegion(x, y, w, h, start.rect);
    }

    canvas.addEventListener("pointerup", finishDrag);
    canvas.addEventListener("pointercancel", function (e) {
      if (!drag || e.pointerId !== drag.pointerId) return;
      drag = null;
      if (mode !== "region") hideBox();
    });

    modal.querySelector(".wc-close-modal").addEventListener("click", closeModal);
    modal.addEventListener("click", function (e) {
      if (e.target === modal) closeModal();
    });
    useBtn.addEventListener("click", function () {
      if (mode === "region" && cropCanvas) {
        useBtn.disabled = true;
        cropCanvas.toBlob(
          function (blob) {
            useBtn.disabled = false;
            if (!blob) {
              window.alert("לא ניתן לשמור את האזור מהתמונה.");
              return;
            }
            var file = new File([blob], "swatch-crop.jpg", { type: "image/jpeg" });
            onPick({ hex: picked, file: file });
            closeModal();
          },
          "image/jpeg",
          0.92
        );
        return;
      }
      if (!picked) {
        window.alert("סמנו אזור בגרירה, או לחצו על נקודה בתמונה");
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
