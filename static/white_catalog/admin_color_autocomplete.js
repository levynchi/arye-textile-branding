(function() {
  "use strict";

  function swatchNode(data, size) {
    if (!data.id || data.loading) {
      return data.text;
    }
    const swatch = data.swatch || (data.element && data.element.dataset.swatch) || "";
    const hex = data.hex || (data.element && data.element.dataset.hex) || "";
    const row = document.createElement("span");
    row.className = "wc-ac-option";
    row.style.display = "inline-flex";
    row.style.alignItems = "center";
    row.style.gap = "8px";
    row.style.maxHeight = "100%";
    const dot = document.createElement("span");
    dot.className = "wc-ac-swatch";
    dot.style.display = "inline-block";
    dot.style.width = size + "px";
    dot.style.height = size + "px";
    dot.style.flex = "0 0 " + size + "px";
    dot.style.borderRadius = "50%";
    dot.style.border = "1px solid #ccc";
    dot.style.backgroundColor = "#f3f3f3";
    dot.style.backgroundSize = "cover";
    dot.style.backgroundPosition = "center";
    dot.style.verticalAlign = "middle";
    if (swatch) {
      dot.style.backgroundImage = 'url("' + String(swatch).replace(/"/g, "%22") + '")';
    } else if (hex) {
      dot.style.backgroundColor = hex;
    }
    const label = document.createElement("span");
    label.textContent = data.text || "";
    row.appendChild(dot);
    row.appendChild(label);
    return row;
  }

  function decorate() {
    const $ = window.django && django.jQuery;
    if (!$ || !$.fn.select2) return;
    $("select.admin-autocomplete").each(function() {
      if (this.dataset.fieldName !== "color") return;
      const $el = $(this);
      if ($el.data("wcSwatch")) return;
      const select2 = $el.data("select2");
      if (!select2 || !select2.options || !select2.options.options) return;
      const options = Object.assign({}, select2.options.options);
      options.templateResult = function(data) { return swatchNode(data, 36); };
      options.templateSelection = function(data) { return swatchNode(data, 20); };
      $el.select2("destroy");
      $el.select2(options);
      $el.data("wcSwatch", true);
    });
  }

  document.addEventListener("DOMContentLoaded", function() {
    setTimeout(decorate, 0);
  });
  document.addEventListener("formset:added", function() {
    setTimeout(decorate, 0);
  });
})();
