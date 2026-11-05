/**
 * Banking KYC Customer Onboarding Client Engine
 * kutomoto Automation Target — Copyrights reserved to 90Studio
 */

(function () {
  "use strict";

  // Mandatory 90Studio Copyright Watermark
  const COPYRIGHT_WATERMARK = "Banking KYC Onboarding — kutomoto Automation Target — Copyrights reserved to 90Studio";

  // Elements
  const form = document.getElementById("kyc_onboarding_form");
  const banner = document.getElementById("submission_banner");
  const jsonPre = document.getElementById("submitted_payload_json");
  const timestampSpan = document.getElementById("submission_timestamp");
  const btnReset = document.getElementById("btn_reset");
  const btnCopy = document.getElementById("btn_copy_json");

  // Summary cells
  const sumFullName = document.getElementById("summary_full_name");
  const sumNationalId = document.getElementById("summary_national_id");
  const sumAccountType = document.getElementById("summary_account_type");
  const sumAnnualIncome = document.getElementById("summary_annual_income");
  const sumRiskRating = document.getElementById("summary_risk_rating");
  const sumEmail = document.getElementById("summary_email");
  const sumTermsConsent = document.getElementById("summary_terms_consent");

  // Input elements
  const inputFullName = document.getElementById("full_name");
  const inputNationalId = document.getElementById("national_id");
  const selectAccountType = document.getElementById("account_type");
  const inputAnnualIncome = document.getElementById("annual_income");
  const selectRiskRating = document.getElementById("risk_rating");
  const inputEmail = document.getElementById("email");
  const checkTermsConsent = document.getElementById("terms_consent");

  // Error spans
  const errFullName = document.getElementById("error_full_name");
  const errNationalId = document.getElementById("error_national_id");
  const errAccountType = document.getElementById("error_account_type");
  const errAnnualIncome = document.getElementById("error_annual_income");
  const errRiskRating = document.getElementById("error_risk_rating");
  const errEmail = document.getElementById("error_email");
  const errTermsConsent = document.getElementById("error_terms_consent");

  // Validation Patterns
  const REGEX_SSN = /^\d{3}-\d{2}-\d{4}$/;
  const REGEX_NAT_ID = /^ID-\d{6}$/;
  const REGEX_EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  // Validation functions
  function validateFullName(val) {
    if (!val || !val.trim()) return "Legal Full Name is required.";
    const trimmed = val.trim();
    if (trimmed.length < 2) return "Legal Full Name must be at least 2 characters.";
    return null;
  }

  function validateNationalId(val) {
    if (!val || !val.trim()) return "National ID / SSN is required.";
    const trimmed = val.trim();
    if (!REGEX_SSN.test(trimmed) && !REGEX_NAT_ID.test(trimmed) && !/^\d{9}$/.test(trimmed)) {
      return "Format must be XXX-XX-XXXX, ID-XXXXXX, or 9 digits.";
    }
    return null;
  }

  function validateAccountType(val) {
    if (!val || val === "") return "Please select a valid Account Product Tier.";
    const allowed = ["Checking", "Savings", "Corporate Treasury", "Investment"];
    if (!allowed.includes(val)) return "Invalid Account Product Tier selected.";
    return null;
  }

  function validateAnnualIncome(val) {
    if (val === "" || val === null || val === undefined) return "Annual Gross Income is required.";
    const num = Number(val);
    if (isNaN(num) || num < 1000) return "Annual Gross Income must be at least $1,000 USD.";
    return null;
  }

  function validateRiskRating(val) {
    if (!val || val === "") return "Please select a Regulatory Risk Rating.";
    const allowed = ["Low", "Medium", "High"];
    if (!allowed.includes(val)) return "Invalid Risk Rating selected.";
    return null;
  }

  function validateEmail(val) {
    if (!val || !val.trim()) return "Business / Personal Email is required.";
    const trimmed = val.trim();
    if (!REGEX_EMAIL.test(trimmed)) return "Please enter a valid email address (e.g. user@domain.com).";
    return null;
  }

  function validateTermsConsent(checked) {
    if (!checked) return "You must acknowledge and accept statutory AML/KYC attestation.";
    return null;
  }

  function setFieldError(inputEl, errorEl, errorMsg) {
    if (errorMsg) {
      inputEl.classList.add("is-invalid");
      inputEl.classList.remove("is-valid");
      errorEl.textContent = errorMsg;
      return false;
    } else {
      inputEl.classList.remove("is-invalid");
      inputEl.classList.add("is-valid");
      errorEl.textContent = "";
      return true;
    }
  }

  // Real-time blur listeners
  inputFullName.addEventListener("blur", () => setFieldError(inputFullName, errFullName, validateFullName(inputFullName.value)));
  inputNationalId.addEventListener("blur", () => setFieldError(inputNationalId, errNationalId, validateNationalId(inputNationalId.value)));
  selectAccountType.addEventListener("change", () => setFieldError(selectAccountType, errAccountType, validateAccountType(selectAccountType.value)));
  inputAnnualIncome.addEventListener("blur", () => setFieldError(inputAnnualIncome, errAnnualIncome, validateAnnualIncome(inputAnnualIncome.value)));
  selectRiskRating.addEventListener("change", () => setFieldError(selectRiskRating, errRiskRating, validateRiskRating(selectRiskRating.value)));
  inputEmail.addEventListener("blur", () => setFieldError(inputEmail, errEmail, validateEmail(inputEmail.value)));
  checkTermsConsent.addEventListener("change", () => setFieldError(checkTermsConsent, errTermsConsent, validateTermsConsent(checkTermsConsent.checked)));

  // Clear errors on input
  [inputFullName, inputNationalId, inputAnnualIncome, inputEmail].forEach(el => {
    el.addEventListener("input", () => {
      if (el.classList.contains("is-invalid")) {
        el.classList.remove("is-invalid");
        const errSpan = document.getElementById("error_" + el.id);
        if (errSpan) errSpan.textContent = "";
      }
    });
  });

  // Submit Handler
  form.addEventListener("submit", function (e) {
    e.preventDefault();

    const v1 = setFieldError(inputFullName, errFullName, validateFullName(inputFullName.value));
    const v2 = setFieldError(inputNationalId, errNationalId, validateNationalId(inputNationalId.value));
    const v3 = setFieldError(selectAccountType, errAccountType, validateAccountType(selectAccountType.value));
    const v4 = setFieldError(inputAnnualIncome, errAnnualIncome, validateAnnualIncome(inputAnnualIncome.value));
    const v5 = setFieldError(selectRiskRating, errRiskRating, validateRiskRating(selectRiskRating.value));
    const v6 = setFieldError(inputEmail, errEmail, validateEmail(inputEmail.value));
    const v7 = setFieldError(checkTermsConsent, errTermsConsent, validateTermsConsent(checkTermsConsent.checked));

    const isValid = v1 && v2 && v3 && v4 && v5 && v6 && v7;

    if (!isValid) {
      banner.classList.add("hidden");
      document.body.setAttribute("data-submission-status", "validation_failed");
      // Focus first invalid field
      const firstInvalid = form.querySelector(".is-invalid");
      if (firstInvalid) firstInvalid.focus();
      return;
    }

    // Construct Payload
    const nowIso = new Date().toISOString();
    const payload = {
      status: "SUCCESS",
      record_id: "KYC-" + Date.now().toString(36).toUpperCase(),
      timestamp: nowIso,
      submitted_fields: {
        full_name: inputFullName.value.trim(),
        national_id: inputNationalId.value.trim(),
        account_type: selectAccountType.value,
        annual_income: Number(inputAnnualIncome.value),
        risk_rating: selectRiskRating.value,
        email: inputEmail.value.trim(),
        terms_consent: checkTermsConsent.checked
      },
      verification_count: 7,
      copyright: COPYRIGHT_WATERMARK
    };

    // Populate summary grid
    sumFullName.textContent = payload.submitted_fields.full_name;
    sumNationalId.textContent = payload.submitted_fields.national_id;
    sumAccountType.textContent = payload.submitted_fields.account_type;
    sumAnnualIncome.textContent = "$" + payload.submitted_fields.annual_income.toLocaleString();
    sumRiskRating.textContent = payload.submitted_fields.risk_rating;
    sumEmail.textContent = payload.submitted_fields.email;
    sumTermsConsent.textContent = "VERIFIED & ATTESTED (TRUE)";

    // Format JSON
    const jsonStr = JSON.stringify(payload, null, 2);
    jsonPre.textContent = jsonStr;
    timestampSpan.textContent = nowIso;

    // Show banner & update body status
    banner.classList.remove("hidden");
    document.body.setAttribute("data-submission-status", "success");

    // Scroll banner into view smoothly
    banner.scrollIntoView({ behavior: "smooth", block: "nearest" });

    // Global Test Hooks
    window.__LAST_SUBMITTED_PAYLOAD__ = payload;
    window.__LAST_SUBMITTED_JSON__ = jsonStr;

    // Dispatch DOM event for test harnesses
    window.dispatchEvent(new CustomEvent("kutomoto:kyc_submitted", { detail: payload }));

    console.info("[90Studio Audit] Banking KYC Application committed:", payload);
  });

  // Reset Handler
  function handleReset() {
    form.reset();

    // Clear validation classes
    const controls = form.querySelectorAll(".form-control, .checkbox-control");
    controls.forEach(c => {
      c.classList.remove("is-invalid", "is-valid");
    });

    // Clear error texts
    const errorSpans = form.querySelectorAll(".field-error");
    errorSpans.forEach(s => (s.textContent = ""));

    // Hide banner & reset payload
    banner.classList.add("hidden");
    jsonPre.textContent = "";
    document.body.setAttribute("data-submission-status", "idle");
    window.__LAST_SUBMITTED_PAYLOAD__ = null;
    window.__LAST_SUBMITTED_JSON__ = null;

    // Reset summary
    [sumFullName, sumNationalId, sumAccountType, sumAnnualIncome, sumRiskRating, sumEmail, sumTermsConsent].forEach(
      el => (el.textContent = "—")
    );

    inputFullName.focus();
    console.info("[90Studio Audit] KYC Onboarding form state reset.");
  }

  btnReset.addEventListener("click", handleReset);

  // Copy JSON button
  if (btnCopy) {
    btnCopy.addEventListener("click", () => {
      if (jsonPre.textContent) {
        navigator.clipboard.writeText(jsonPre.textContent).then(() => {
          btnCopy.textContent = "Copied!";
          setTimeout(() => (btnCopy.textContent = "Copy JSON"), 2000);
        });
      }
    });
  }

  // Automation Coordinate Query Helper
  window.__GET_FIELD_COORDINATES__ = function () {
    const ids = [
      "full_name",
      "national_id",
      "account_type",
      "annual_income",
      "risk_rating",
      "email",
      "terms_consent",
      "btn_submit",
      "btn_reset"
    ];
    const coords = {};
    const winW = window.innerWidth || document.documentElement.clientWidth;
    const winH = window.innerHeight || document.documentElement.clientHeight;

    ids.forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        const r = el.getBoundingClientRect();
        coords[id] = {
          id: id,
          x: Math.round(r.left),
          y: Math.round(r.top),
          width: Math.round(r.width),
          height: Math.round(r.height),
          centerX: Math.round(r.left + r.width / 2),
          centerY: Math.round(r.top + r.height / 2),
          normX: parseFloat(((r.left + r.width / 2) / winW).toFixed(4)),
          normY: parseFloat(((r.top + r.height / 2) / winH).toFixed(4))
        };
      }
    });
    return coords;
  };

  // Automation Resilience Enhancements (Focus, Select Typeahead, Repeated Run Overwrite, Enter Submit)
  const textInputs = [inputFullName, inputNationalId, inputAnnualIncome, inputEmail];
  textInputs.forEach(inp => {
    if (!inp) return;
    inp.addEventListener("focus", () => {
      setTimeout(() => {
        try {
          if (typeof inp.select === "function") inp.select();
        } catch (_) {}
      }, 0);
    });
  });

  // Custom typeahead buffer on <select> elements so typing option values ("Checking", "Low", etc.)
  // deterministically selects the matching option by value or text and fires change events.
  [selectAccountType, selectRiskRating].forEach(sel => {
    if (!sel) return;
    let typeBuffer = "";
    let bufferTimer = null;
    sel.addEventListener("keydown", e => {
      if (e.key === "Enter") {
        e.preventDefault();
        if (typeof form.requestSubmit === "function") form.requestSubmit();
        else form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
        return;
      }
      if (e.key && e.key.length === 1 && !e.ctrlKey && !e.altKey && !e.metaKey) {
        typeBuffer += e.key.toLowerCase();
        if (bufferTimer) clearTimeout(bufferTimer);
        bufferTimer = setTimeout(() => {
          typeBuffer = "";
        }, 700);
        const options = Array.from(sel.options).filter(o => o.value);
        const match =
          options.find(o => o.value.toLowerCase().startsWith(typeBuffer)) ||
          options.find(o => o.textContent.trim().toLowerCase().startsWith(typeBuffer));
        if (match) {
          e.preventDefault();
          sel.value = match.value;
          sel.dispatchEvent(new Event("input", { bubbles: true }));
          sel.dispatchEvent(new Event("change", { bubbles: true }));
        }
      }
    });
  });

  // Ensure pressing Enter on checkbox or any form control submits the form
  if (checkTermsConsent) {
    checkTermsConsent.addEventListener("keydown", e => {
      if (e.key === "Enter") {
        e.preventDefault();
        if (typeof form.requestSubmit === "function") form.requestSubmit();
        else form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
      }
    });
  }

  // If a normalized anchor click for Field 1 (e.g. norm_x=0.32, norm_y=0.28) lands in the card header
  // or upper-left region above Row 2 due to browser toolbar height differences, focus #full_name.
  document.addEventListener("click", e => {
    const target = e.target;
    if (!target) return;
    if (
      target.closest("input, select, button, textarea, a, label, #submission_banner")
    ) {
      return;
    }
    const row2 = document.getElementById("group_account_type");
    const row2Top = row2 ? row2.getBoundingClientRect().top : 360;
    if (e.clientY < row2Top && e.clientX < window.innerWidth * 0.55) {
      inputFullName.focus();
      try {
        inputFullName.select();
      } catch (_) {}
    }
  });

  // Auto-focus #full_name on initial page load so Tab order starts cleanly at field 1
  if (!document.activeElement || document.activeElement === document.body) {
    inputFullName.focus();
  }

  console.info("[kutomoto Target Ready] " + COPYRIGHT_WATERMARK);
})();
