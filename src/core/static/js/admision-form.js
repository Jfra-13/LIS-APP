/**
 * admision-form.js
 * Patient form UX: document-type placeholder switching, phone prefix,
 * digit-block on name fields, Ctrl+S save, ESC cancel.
 *
 * Loaded only on paciente_form.html. Requires data-* attrs injected by the
 * template for dynamic field IDs (see template script tag).
 */

(function () {
  "use strict";

  // Keyboard shortcuts
  document.addEventListener("keydown", function (event) {
    if (event.ctrlKey && event.key === "s") {
      event.preventDefault();
      var form = document.querySelector("form");
      if (form) form.submit();
    }
    if (event.key === "Escape") {
      window.history.back();
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    // Field IDs are injected by the template via data attributes on the
    // script tag, or we fall back to the Django-generated id_<fieldname>.
    var tipoDocSelect = document.getElementById("id_tipo_documento");
    var dniInput = document.getElementById("id_dni");
    var telefonoInput = document.getElementById("id_telefono");
    var prefijoInput = document.getElementById("id_telefono_prefijo");
    var nombresInput = document.getElementById("id_nombres");
    var apellidosInput = document.getElementById("id_apellidos");

    // --- Document type → DNI placeholder / maxlength ---
    function updateDniPlaceholder() {
      if (!tipoDocSelect || !dniInput) return;
      var tipo = tipoDocSelect.value;
      if (tipo === "DNI") {
        dniInput.placeholder = "Ej. 12345678 (8 dígitos)";
        dniInput.maxLength = 8;
      } else if (tipo === "PAS") {
        dniInput.placeholder = "Número de Pasaporte";
        dniInput.maxLength = 15;
      } else if (tipo === "CE") {
        dniInput.placeholder = "Carné de Extranjería";
        dniInput.maxLength = 12;
      }
    }

    if (tipoDocSelect) {
      tipoDocSelect.addEventListener("change", updateDniPlaceholder);
      updateDniPlaceholder();
    }

    // --- Phone: national number is digits-only; capped at 9 only when +51 ---
    function currentPrefijo() {
      return prefijoInput ? prefijoInput.value.trim() : "+51";
    }
    function enforcePhone() {
      if (!telefonoInput) return;
      var digits = telefonoInput.value.replace(/\D/g, "");
      if (currentPrefijo() === "+51") {
        digits = digits.slice(0, 9);
      }
      telefonoInput.value = digits;
    }
    if (telefonoInput) {
      telefonoInput.addEventListener("input", enforcePhone);
    }
    if (prefijoInput) {
      // Keep a leading "+" that can't be deleted; digits after it are editable.
      prefijoInput.addEventListener("input", function () {
        this.value = "+" + this.value.replace(/\D/g, "");
        enforcePhone();
      });
    }

    // --- Block digits in name fields ---
    [nombresInput, apellidosInput].forEach(function (input) {
      if (!input) return;
      input.addEventListener("input", function () {
        this.value = this.value.replace(/[0-9]/g, "");
      });
    });
  });
})();
