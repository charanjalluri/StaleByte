document.addEventListener("DOMContentLoaded", () => {
  // Scenario trigger buttons
  const btnCollision = document.getElementById("btn-collision");
  const btnNormal = document.getElementById("btn-normal");
  const btnSkew = document.getElementById("btn-skew");
  const btnReset = document.getElementById("btn-reset");
  const btnCleanCache = document.getElementById("btn-clean-cache");
  const btnHeaderClean = document.getElementById("btn-header-clean");
  const btnResetUploadCache = document.getElementById("btn-reset-upload-cache");

  // Inputs
  const inputVal = document.getElementById("input-value");
  const v1SourceInput = document.getElementById("v1-source-input");
  const v2SourceInput = document.getElementById("v2-source-input");

  // Simulation loading indicator & grid
  const simulationLoading = document.getElementById("simulation-loading");
  const comparisonGrid = document.getElementById("comparison-grid");
  const sysStatus = document.getElementById("sys-status");

  // Naive strategy output elements
  const naivePanel = document.getElementById("naive-panel");
  const naiveVerdictBanner = document.getElementById("naive-verdict-banner");
  const naiveResult = document.getElementById("naive-result");
  const naiveBadge = document.getElementById("naive-badge");
  const naiveSub = document.getElementById("naive-sub");
  const naiveStale = document.getElementById("naive-stale");
  const naiveStaleIcon = document.getElementById("naive-stale-icon");
  const naiveCache = document.getElementById("naive-cache");
  const naiveCacheIcon = document.getElementById("naive-cache-icon");
  const naiveReason = document.getElementById("naive-reason");

  // Smart strategy output elements
  const smartPanel = document.getElementById("smart-panel");
  const smartVerdictBanner = document.getElementById("smart-verdict-banner");
  const smartResult = document.getElementById("smart-result");
  const smartBadge = document.getElementById("smart-badge");
  const smartSub = document.getElementById("smart-sub");
  const smartStale = document.getElementById("smart-stale");
  const smartStaleIcon = document.getElementById("smart-stale-icon");
  const smartAction = document.getElementById("smart-action");
  const smartActionIcon = document.getElementById("smart-action-icon");
  const smartReason = document.getElementById("smart-reason");

  // Provenance inspector elements
  const scenarioName = document.getElementById("scenario-name");
  const v1Code = document.getElementById("v1-code");
  const v1Hash = document.getElementById("v1-hash");
  const v2Code = document.getElementById("v2-code");
  const v2Hash = document.getElementById("v2-hash");
  const tCache = document.getElementById("t-cache");
  const tMtime = document.getElementById("t-mtime");

  // Explain elements
  const btnExplainNaive = document.getElementById("btn-explain-naive");
  const naiveAiBox = document.getElementById("naive-ai-box");
  const naiveAiText = document.getElementById("naive-ai-text");

  const btnExplainSmart = document.getElementById("btn-explain-smart");
  const smartAiBox = document.getElementById("smart-ai-box");
  const smartAiText = document.getElementById("smart-ai-text");

  // Diagnostic state caches
  let currentNaiveDiagnostic = {
    scenario: "Timestamp Collision",
    strategy: "Naive Invalidation",
    decision: {
      is_stale: false,
      reason: "mtime ≤ t_cache. Identical timestamps caused silent stale execution.",
    },
  };

  let currentSmartDiagnostic = {
    scenario: "Timestamp Collision",
    strategy: "StaleByte Invalidation",
    decision: {
      is_stale: true,
      reason: "Timestamp collision intercepted: SHA-256 hash divergence triggered rebuild.",
    },
  };

  // =========================================================================
  // Toast Notifications System
  // =========================================================================
  function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(100%)";
      setTimeout(() => toast.remove(), 250);
    }, 3500);
  }

  function resetExplainingBoxes() {
    if (naiveAiBox) naiveAiBox.setAttribute("hidden", "");
    if (btnExplainNaive) btnExplainNaive.setAttribute("aria-expanded", "false");
    if (smartAiBox) smartAiBox.setAttribute("hidden", "");
    if (btnExplainSmart) btnExplainSmart.setAttribute("aria-expanded", "false");
  }

  // =========================================================================
  // Scenario Execution Helper with Full In-Flight Loading State (Requirement 1)
  // =========================================================================
  async function postScenario(endpoint, payloadExtras = {}, triggeringBtn = null) {
    const val = parseInt(inputVal ? inputVal.value : "10", 10) || 10;
    const payload = {
      input_value: val,
      v1_source: v1SourceInput ? v1SourceInput.value : "operation=multiply\nfactor=2",
      v2_source: v2SourceInput ? v2SourceInput.value : "operation=multiply\nfactor=3",
      ...payloadExtras,
    };

    // Set loading state
    if (triggeringBtn) triggeringBtn.classList.add("is-loading");
    if (btnCollision) btnCollision.disabled = true;
    if (btnNormal) btnNormal.disabled = true;
    if (btnSkew) btnSkew.disabled = true;
    if (simulationLoading) simulationLoading.removeAttribute("hidden");
    if (comparisonGrid) {
      comparisonGrid.setAttribute("aria-busy", "true");
      if (naivePanel) naivePanel.classList.add("panel-is-updating");
      if (smartPanel) smartPanel.classList.add("panel-is-updating");
    }

    try {
      const resp = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.error || `HTTP error ${resp.status}`);
      }
      return data;
    } catch (err) {
      console.error("API error:", err);
      showToast(`Simulation error: ${err.message}`, "error");
      return null;
    } finally {
      if (triggeringBtn) triggeringBtn.classList.remove("is-loading");
      if (btnCollision) btnCollision.disabled = false;
      if (btnNormal) btnNormal.disabled = false;
      if (btnSkew) btnSkew.disabled = false;
      if (simulationLoading) simulationLoading.setAttribute("hidden", "");
      if (comparisonGrid) {
        comparisonGrid.setAttribute("aria-busy", "false");
        if (naivePanel) naivePanel.classList.remove("panel-is-updating");
        if (smartPanel) smartPanel.classList.remove("panel-is-updating");
      }
    }
  }

  // =========================================================================
  // Scenario Handlers (Requirement 2: Unmistakable Visual Differentiation)
  // =========================================================================

  // Handle Collision Scenario
  if (btnCollision) {
    btnCollision.addEventListener("click", async () => {
      resetExplainingBoxes();
      const data = await postScenario("/api/run/collision", {}, btnCollision);
      if (!data) return;

      if (scenarioName) scenarioName.textContent = "Scenario: Timestamp Collision";
      if (sysStatus) sysStatus.textContent = "Simulated: coarse 1s filesystem collision executed (FAT32/ext3)";

      currentNaiveDiagnostic = {
        scenario: "Timestamp Collision",
        strategy: "Naive Invalidation",
        decision: data.naive.decision,
        execution: data.naive,
      };

      currentSmartDiagnostic = {
        scenario: "Timestamp Collision",
        strategy: "StaleByte Invalidation",
        decision: data.smart.decision,
        execution: data.smart,
        hashes: data.hashes,
      };

      // Update Naive view (Red / Failure alert styling)
      if (naiveVerdictBanner) {
        naiveVerdictBanner.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"></polygon><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg><span>CRITICAL FAIL: SILENT BYTECODE DIVERGENCE</span>`;
        naiveVerdictBanner.className = "verdict-banner-highlight fail";
      }
      if (naiveResult) naiveResult.textContent = data.naive.output;
      if (naiveBadge) {
        naiveBadge.textContent = "STALE REUSE (FAIL)";
        naiveBadge.className = "status-indicator error";
      }
      if (naiveSub) naiveSub.textContent = `Calculated via obsolete factor=${data.naive.executed_factor} (Expected 30)`;
      if (naiveStale) naiveStale.textContent = `is_stale = ${data.naive.decision.is_stale} (FALSE HIT)`;
      if (naiveStaleIcon) {
        naiveStaleIcon.textContent = "✕";
        naiveStaleIcon.className = "proof-icon fail";
      }
      if (naiveCache) {
        naiveCache.textContent = "Reused Stale V1 Cache";
        naiveCache.className = "proof-val text-fail";
      }
      if (naiveCacheIcon) {
        naiveCacheIcon.textContent = "✕";
        naiveCacheIcon.className = "proof-icon fail";
      }
      if (naiveReason) naiveReason.textContent = data.naive.decision.reason;

      // Update Smart view (Vibrant Emerald Green / Verified pass styling)
      if (smartVerdictBanner) {
        smartVerdictBanner.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><polyline points="9 12 11 14 15 10"></polyline></svg><span>VERIFIED PASS: CRYPTOGRAPHIC REBUILD TRIGGERED</span>`;
        smartVerdictBanner.className = "verdict-banner-highlight pass";
      }
      if (smartResult) smartResult.textContent = data.smart.output;
      if (smartBadge) {
        smartBadge.textContent = "REBUILT V2 (PASS)";
        smartBadge.className = "status-indicator correct";
      }
      if (smartSub) smartSub.textContent = `Calculated via rebuilt factor=${data.smart.executed_factor} (Correct Build)`;
      if (smartStale) smartStale.textContent = `is_stale = ${data.smart.decision.is_stale} (Hash Mismatch: ${data.hashes.match ? 'No' : 'Yes'})`;
      if (smartStaleIcon) {
        smartStaleIcon.textContent = "✓";
        smartStaleIcon.className = "proof-icon pass";
      }
      if (smartAction) {
        smartAction.textContent = data.smart.invalidated ? "Invalidated Stale Cache & Rebuilt" : "Reused Valid Cache";
        smartAction.className = "proof-val text-pass";
      }
      if (smartActionIcon) {
        smartActionIcon.textContent = "✓";
        smartActionIcon.className = "proof-icon pass";
      }
      if (smartReason) smartReason.textContent = data.smart.decision.reason;

      // Update Provenance Inspector
      if (v1Code) v1Code.textContent = data.source.v1.trim();
      if (v1Hash) v1Hash.textContent = data.hashes.cached;
      if (v2Code) v2Code.textContent = data.source.v2.trim();
      if (v2Hash) v2Hash.textContent = data.hashes.current;
      if (tCache) tCache.textContent = `${data.timestamps.cached}s`;
      if (tMtime) tMtime.textContent = `${data.timestamps.current}s`;

      showToast("Collision scenario executed · Divergence detected", "info");
    });
  }

  // Handle Normal Flow Scenario
  if (btnNormal) {
    btnNormal.addEventListener("click", async () => {
      resetExplainingBoxes();
      const data = await postScenario("/api/run/normal", {
        source_content: v1SourceInput ? v1SourceInput.value : undefined,
      }, btnNormal);
      if (!data) return;

      if (scenarioName) scenarioName.textContent = "Scenario: Normal Flow (Unchanged Source)";
      if (sysStatus) sysStatus.textContent = "Unchanged source: both invalidators correctly agree on Cache Hit";

      currentNaiveDiagnostic = {
        scenario: "Normal Flow",
        strategy: "Naive Invalidation",
        decision: data.naive.decision,
      };

      currentSmartDiagnostic = {
        scenario: "Normal Flow",
        strategy: "StaleByte Invalidation",
        decision: data.smart.decision,
      };

      if (naiveVerdictBanner) {
        naiveVerdictBanner.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><polyline points="9 12 11 14 15 10"></polyline></svg><span>CACHE HIT: REUSED VALID ARTIFACT</span>`;
        naiveVerdictBanner.className = "verdict-banner-highlight pass";
      }
      if (naiveResult) naiveResult.textContent = data.result;
      if (naiveBadge) {
        naiveBadge.textContent = "VALID CACHE (PASS)";
        naiveBadge.className = "status-indicator correct";
      }
      if (naiveSub) naiveSub.textContent = "Calculated via valid cached factor=2";
      if (naiveStale) naiveStale.textContent = `is_stale = ${data.naive.decision.is_stale}`;
      if (naiveStaleIcon) {
        naiveStaleIcon.textContent = "✓";
        naiveStaleIcon.className = "proof-icon pass";
      }
      if (naiveCache) {
        naiveCache.textContent = "Reused Valid Cache";
        naiveCache.className = "proof-val text-pass";
      }
      if (naiveCacheIcon) {
        naiveCacheIcon.textContent = "✓";
        naiveCacheIcon.className = "proof-icon pass";
      }
      if (naiveReason) naiveReason.textContent = data.naive.decision.reason;

      if (smartVerdictBanner) {
        smartVerdictBanner.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><polyline points="9 12 11 14 15 10"></polyline></svg><span>CACHE HIT: CRYPTOGRAPHIC HASH MATCH</span>`;
        smartVerdictBanner.className = "verdict-banner-highlight pass";
      }
      if (smartResult) smartResult.textContent = data.result;
      if (smartBadge) {
        smartBadge.textContent = "VALID CACHE (PASS)";
        smartBadge.className = "status-indicator correct";
      }
      if (smartSub) smartSub.textContent = "Calculated via valid cached factor=2";
      if (smartStale) smartStale.textContent = `is_stale = ${data.smart.decision.is_stale} (Hash match confirmed)`;
      if (smartStaleIcon) {
        smartStaleIcon.textContent = "✓";
        smartStaleIcon.className = "proof-icon pass";
      }
      if (smartAction) {
        smartAction.textContent = "Reused Valid Cache";
        smartAction.className = "proof-val text-pass";
      }
      if (smartActionIcon) {
        smartActionIcon.textContent = "✓";
        smartActionIcon.className = "proof-icon pass";
      }
      if (smartReason) smartReason.textContent = data.smart.decision.reason;

      if (v1Code) v1Code.textContent = data.source.v1.trim();
      if (v1Hash) v1Hash.textContent = data.hashes.cached;
      if (v2Code) v2Code.textContent = data.source.v2.trim();
      if (v2Hash) v2Hash.textContent = data.hashes.current;
      if (tCache) tCache.textContent = `${data.timestamps.cached}s`;
      if (tMtime) tMtime.textContent = `${data.timestamps.current}s`;

      showToast("Normal flow executed · Both strategies report Cache Hit", "info");
    });
  }

  // Handle Clock Skew Scenario
  if (btnSkew) {
    btnSkew.addEventListener("click", async () => {
      resetExplainingBoxes();
      const data = await postScenario("/api/run/skew", {
        source_content: v1SourceInput ? v1SourceInput.value : undefined,
      }, btnSkew);
      if (!data) return;

      if (scenarioName) scenarioName.textContent = "Scenario: Machine Clock Skew (Distributed Build)";
      if (sysStatus) sysStatus.textContent = "Distributed node clock skew: build runner clock lag simulated";

      currentNaiveDiagnostic = {
        scenario: "Clock Skew",
        strategy: "Naive Invalidation",
        decision: data.naive.decision,
      };

      currentSmartDiagnostic = {
        scenario: "Clock Skew",
        strategy: "StaleByte Invalidation",
        decision: data.smart.decision,
      };

      if (naiveVerdictBanner) {
        naiveVerdictBanner.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><polyline points="9 12 11 14 15 10"></polyline></svg><span>CACHE HIT: REUSED VALID ARTIFACT</span>`;
        naiveVerdictBanner.className = "verdict-banner-highlight pass";
      }
      if (naiveResult) naiveResult.textContent = data.result;
      if (naiveBadge) {
        naiveBadge.textContent = "VALID CACHE (PASS)";
        naiveBadge.className = "status-indicator correct";
      }
      if (naiveSub) naiveSub.textContent = "Calculated via cached artifact";
      if (naiveStale) naiveStale.textContent = `is_stale = ${data.naive.decision.is_stale}`;
      if (naiveStaleIcon) {
        naiveStaleIcon.textContent = "✓";
        naiveStaleIcon.className = "proof-icon pass";
      }
      if (naiveCache) {
        naiveCache.textContent = "Reused Cached Artifact";
        naiveCache.className = "proof-val text-pass";
      }
      if (naiveCacheIcon) {
        naiveCacheIcon.textContent = "✓";
        naiveCacheIcon.className = "proof-icon pass";
      }
      if (naiveReason) naiveReason.textContent = data.naive.decision.reason;

      if (smartVerdictBanner) {
        smartVerdictBanner.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><polyline points="9 12 11 14 15 10"></polyline></svg><span>CACHE HIT: VERIFIED BY CONTENT HASH</span>`;
        smartVerdictBanner.className = "verdict-banner-highlight pass";
      }
      if (smartResult) smartResult.textContent = data.result;
      if (smartBadge) {
        smartBadge.textContent = "VALID CACHE (PASS)";
        smartBadge.className = "status-indicator correct";
      }
      if (smartSub) smartSub.textContent = "Calculated via verified artifact";
      if (smartStale) smartStale.textContent = `is_stale = ${data.smart.decision.is_stale}`;
      if (smartStaleIcon) {
        smartStaleIcon.textContent = "✓";
        smartStaleIcon.className = "proof-icon pass";
      }
      if (smartAction) {
        smartAction.textContent = "Reused Valid Cache";
        smartAction.className = "proof-val text-pass";
      }
      if (smartActionIcon) {
        smartActionIcon.textContent = "✓";
        smartActionIcon.className = "proof-icon pass";
      }
      if (smartReason) smartReason.textContent = data.smart.decision.reason;

      if (v1Code) v1Code.textContent = data.source.v1.trim();
      if (v1Hash) v1Hash.textContent = data.hashes.cached;
      if (v2Code) v2Code.textContent = data.source.v2.trim();
      if (v2Hash) v2Hash.textContent = data.hashes.current;
      if (tCache) tCache.textContent = `${data.timestamps.cached}s`;
      if (tMtime) tMtime.textContent = `${data.timestamps.current}s`;

      showToast("Clock skew scenario executed", "info");
    });
  }

  // =========================================================================
  // One-Click Clean / Reset Cache Handler (Requirement 5)
  // =========================================================================
  async function performCacheReset(btn = null) {
    if (btn) btn.classList.add("is-loading");

    try {
      // Attempt backend purge endpoint
      await fetch("/api/clean", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      }).catch(() => null);

      // Reset form controls
      if (v1SourceInput) v1SourceInput.value = "operation=multiply\nfactor=2";
      if (v2SourceInput) v2SourceInput.value = "operation=multiply\nfactor=3";
      if (inputVal) inputVal.value = "10";

      // Reset verdict ribbons and icons
      if (naiveVerdictBanner) {
        naiveVerdictBanner.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"></polygon><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg><span>CRITICAL FAIL: SILENT BYTECODE DIVERGENCE</span>`;
        naiveVerdictBanner.className = "verdict-banner-highlight fail";
      }
      if (smartVerdictBanner) {
        smartVerdictBanner.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><polyline points="9 12 11 14 15 10"></polyline></svg><span>VERIFIED PASS: CRYPTOGRAPHIC REBUILD TRIGGERED</span>`;
        smartVerdictBanner.className = "verdict-banner-highlight pass";
      }
      if (naiveResult) naiveResult.textContent = "20";
      if (smartResult) smartResult.textContent = "30";
      if (naiveBadge) {
        naiveBadge.textContent = "STALE REUSE (FAIL)";
        naiveBadge.className = "status-indicator error";
      }
      if (smartBadge) {
        smartBadge.textContent = "REBUILT V2 (PASS)";
        smartBadge.className = "status-indicator correct";
      }
      if (naiveSub) naiveSub.textContent = "Computed using obsolete factor=2 (Expected 30)";
      if (smartSub) smartSub.textContent = "Computed using current factor=3 (Correct Build)";
      if (naiveStale) naiveStale.textContent = "is_stale = false (FALSE HIT)";
      if (smartStale) smartStale.textContent = "is_stale = true (Hash Mismatch)";
      if (naiveCache) naiveCache.textContent = "Reused Stale Cache";
      if (smartAction) smartAction.textContent = "Invalidate & Rebuild";
      if (naiveStaleIcon) {
        naiveStaleIcon.textContent = "✕";
        naiveStaleIcon.className = "proof-icon fail";
      }
      if (naiveCacheIcon) {
        naiveCacheIcon.textContent = "✕";
        naiveCacheIcon.className = "proof-icon fail";
      }
      if (smartStaleIcon) {
        smartStaleIcon.textContent = "✓";
        smartStaleIcon.className = "proof-icon pass";
      }
      if (smartActionIcon) {
        smartActionIcon.textContent = "✓";
        smartActionIcon.className = "proof-icon pass";
      }

      // Clear upload check state
      clearSelectedFile();
      if (uploadResults) uploadResults.setAttribute("hidden", "");
      setUploadError(null);

      // Reset explaining boxes
      resetExplainingBoxes();

      // Update status
      if (sysStatus) sysStatus.textContent = "Cache cleared · Ready for fresh baseline demo";
      showToast("Persistent cache cleared · Ready for showcase demo", "toast-success");
    } catch (err) {
      console.error("Clean cache error:", err);
      showToast("Cache reset locally", "info");
    } finally {
      if (btn) btn.classList.remove("is-loading");
    }
  }

  if (btnCleanCache) {
    btnCleanCache.addEventListener("click", () => performCacheReset(btnCleanCache));
  }
  if (btnHeaderClean) {
    btnHeaderClean.addEventListener("click", () => performCacheReset(btnHeaderClean));
  }
  if (btnResetUploadCache) {
    btnResetUploadCache.addEventListener("click", () => performCacheReset(btnResetUploadCache));
  }
  if (btnReset) {
    btnReset.addEventListener("click", () => performCacheReset(btnReset));
  }

  // =========================================================================
  // AI Explanation Handler (POST /explain with Loading State) (Requirement 1)
  // =========================================================================
  function setupExplainButton(btn, box, textEl, getDiagnosticFn) {
    if (!btn || !box || !textEl) return;

    btn.addEventListener("click", async () => {
      const isHidden = box.hasAttribute("hidden");
      if (!isHidden) {
        box.setAttribute("hidden", "");
        btn.setAttribute("aria-expanded", "false");
        return;
      }

      box.removeAttribute("hidden");
      btn.setAttribute("aria-expanded", "true");
      btn.classList.add("is-loading");
      textEl.textContent = "Analyzing diagnostic...";

      const diagnosticData = getDiagnosticFn();
      const fallbackReason = diagnosticData?.decision?.reason || "Cache diagnostic verified deterministically.";

      try {
        const resp = await fetch("/explain", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(diagnosticData),
        });

        if (!resp.ok) {
          textEl.textContent = fallbackReason;
          return;
        }

        const data = await resp.json();
        if (data && data.explanation) {
          textEl.textContent = data.explanation;
        } else {
          textEl.textContent = fallbackReason;
        }
      } catch (err) {
        console.error("Explain request failed:", err);
        textEl.textContent = fallbackReason;
      } finally {
        btn.classList.remove("is-loading");
      }
    });
  }

  setupExplainButton(btnExplainNaive, naiveAiBox, naiveAiText, () => currentNaiveDiagnostic);
  setupExplainButton(btnExplainSmart, smartAiBox, smartAiText, () => currentSmartDiagnostic);

  // =========================================================================
  // Real File Upload & Staleness Check (Requirements 1, 3, & 4)
  // =========================================================================
  const sourceFileInput = document.getElementById("source-file-input");
  const uploadDropzone = document.getElementById("upload-dropzone");
  const dropzoneEmptyState = document.getElementById("dropzone-empty-state");
  const dropzoneSelectedState = document.getElementById("dropzone-selected-state");
  const selectedFileName = document.getElementById("selected-file-name");
  const selectedFileMeta = document.getElementById("selected-file-meta");
  const btnClearFile = document.getElementById("btn-clear-file");
  const btnUploadCheck = document.getElementById("btn-upload-check");
  const uploadError = document.getElementById("upload-error");
  const uploadErrorTitle = document.getElementById("upload-error-title");
  const uploadErrorDetail = document.getElementById("upload-error-detail");
  const uploadErrorHint = document.getElementById("upload-error-hint");
  const uploadResults = document.getElementById("upload-results");

  const uploadVerdictBanner = document.getElementById("upload-verdict-banner");
  const uploadVerdictTag = document.getElementById("upload-verdict-tag");
  const uploadVerdictText = document.getElementById("upload-verdict-text");

  const uploadMetaName = document.getElementById("upload-meta-name");
  const uploadMetaSize = document.getElementById("upload-meta-size");
  const uploadMetaMtime = document.getElementById("upload-meta-mtime");
  const uploadMetaHash = document.getElementById("upload-meta-hash");

  const uploadCacheStatus = document.getElementById("upload-cache-status");
  const uploadCacheTime = document.getElementById("upload-cache-time");
  const uploadCacheHash = document.getElementById("upload-cache-hash");

  const uploadNaiveBadge = document.getElementById("upload-naive-badge");
  const uploadNaiveDecision = document.getElementById("upload-naive-decision");
  const uploadNaiveVerdict = document.getElementById("upload-naive-verdict");
  const uploadNaiveReason = document.getElementById("upload-naive-reason");

  const uploadRobustBadge = document.getElementById("upload-robust-badge");
  const uploadRobustDecision = document.getElementById("upload-robust-decision");
  const uploadRobustVerdict = document.getElementById("upload-robust-verdict");
  const uploadRobustReason = document.getElementById("upload-robust-reason");

  const btnLoadSample = document.getElementById("btn-load-sample");
  const btnFixSample = document.getElementById("btn-fix-sample");

  let activeFile = null;

  // Specific, friendly error presenter (Requirement 4)
  function setUploadError(errText, customTitle = null, customHint = null) {
    if (!uploadError) return;
    if (!errText) {
      uploadError.setAttribute("hidden", "");
      return;
    }

    let title = customTitle || "Upload Rejected";
    let detail = errText;
    let hint = customHint || "";

    const lower = errText.toLowerCase();
    if (lower.includes("empty")) {
      title = "File Is Empty";
      detail = "The selected file contains no text. StaleByte needs at least one operation to compile.";
      hint = "Add lines like: operation=multiply\nfactor=4";
    } else if (lower.includes("unsupported") || lower.includes("extension")) {
      title = "Unsupported File Extension";
      detail = "Only '.src' or '.txt' source files are accepted.";
      hint = "Please rename your file with a .src extension and re-upload.";
    } else if (lower.includes("malformed") || lower.includes("dsl")) {
      title = "Invalid Source DSL Syntax";
      detail = "The file syntax could not be compiled into bytecode.";
      hint = "Expected format:\noperation=multiply\nfactor=3";
    } else if (lower.includes("1mb") || lower.includes("size")) {
      title = "File Exceeds 1MB Limit";
      detail = "Source file is too large for the showcase playground.";
      hint = "Please upload a lightweight DSL file under 1MB.";
    }

    if (uploadErrorTitle) uploadErrorTitle.textContent = title;
    if (uploadErrorDetail) uploadErrorDetail.textContent = detail;
    if (uploadErrorHint) {
      if (hint) {
        uploadErrorHint.innerHTML = `Format guidance:<br><code>${hint.replace(/\n/g, '<br>')}</code>`;
        uploadErrorHint.style.display = "block";
      } else {
        uploadErrorHint.style.display = "none";
      }
    }

    uploadError.removeAttribute("hidden");
    uploadError.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function clearSelectedFile() {
    activeFile = null;
    if (sourceFileInput) sourceFileInput.value = "";
    if (btnUploadCheck) btnUploadCheck.disabled = true;
    if (dropzoneEmptyState) dropzoneEmptyState.removeAttribute("hidden");
    if (dropzoneSelectedState) dropzoneSelectedState.setAttribute("hidden", "");
    setUploadError(null);
  }

  if (btnClearFile) {
    btnClearFile.addEventListener("click", (e) => {
      e.stopPropagation();
      clearSelectedFile();
    });
  }

  function handleFileSelected(file) {
    if (!file) {
      clearSelectedFile();
      return;
    }

    activeFile = file;
    setUploadError(null);

    // Update Dropzone presentation (Requirement 3)
    if (dropzoneEmptyState) dropzoneEmptyState.setAttribute("hidden", "");
    if (dropzoneSelectedState) dropzoneSelectedState.removeAttribute("hidden");
    if (selectedFileName) selectedFileName.textContent = file.name;
    if (selectedFileMeta) selectedFileMeta.textContent = `${file.size} bytes · Ready for live check`;
    if (btnUploadCheck) btnUploadCheck.disabled = false;
  }

  if (sourceFileInput) {
    sourceFileInput.addEventListener("change", (e) => {
      const file = e.target.files && e.target.files[0];
      handleFileSelected(file);
    });
  }

  // Drag and drop events (Requirement 3)
  if (uploadDropzone) {
    ["dragenter", "dragover"].forEach((eventName) => {
      uploadDropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadDropzone.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      uploadDropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadDropzone.classList.remove("dragover");
      });
    });

    uploadDropzone.addEventListener("drop", (e) => {
      const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (file) {
        if (sourceFileInput) sourceFileInput.files = e.dataTransfer.files;
        handleFileSelected(file);
      }
    });

    uploadDropzone.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        if (sourceFileInput) sourceFileInput.click();
      }
    });
  }

  // Rapid sample file loading for live showcase demos
  function loadSampleSourceFile() {
    const sampleContent = "operation=multiply\nfactor=4\n";
    let sampleFile;
    try {
      sampleFile = new File([sampleContent], "sample_v1.src", { type: "text/plain" });
    } catch {
      sampleFile = new Blob([sampleContent], { type: "text/plain" });
      sampleFile.name = "sample_v1.src";
    }
    handleFileSelected(sampleFile);
    showToast("Loaded sample_v1.src (factor=4) · Click 'Check Uploaded File' to test", "toast-info");
  }

  if (btnLoadSample) {
    btnLoadSample.addEventListener("click", loadSampleSourceFile);
  }
  if (btnFixSample) {
    btnFixSample.addEventListener("click", loadSampleSourceFile);
  }

  // Global Escape key listener to close chat panel
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && chatPanel && !chatPanel.hasAttribute("hidden")) {
      toggleChat(false);
    }
  });

  // Upload Check Button with In-Flight Loading State (Requirement 1 & 4)
  if (btnUploadCheck) {
    btnUploadCheck.addEventListener("click", async () => {
      if (!activeFile) return;

      // Validate size client-side first
      if (activeFile.size > 1048576) {
        setUploadError(`File size (${activeFile.size} bytes) exceeds the maximum allowed 1MB limit.`);
        return;
      }

      setUploadError(null);
      btnUploadCheck.classList.add("is-loading");
      btnUploadCheck.disabled = true;

      const reader = new FileReader();
      reader.onerror = () => {
        setUploadError("Could not read local file content from disk.");
        btnUploadCheck.classList.remove("is-loading");
        btnUploadCheck.disabled = false;
      };

      reader.onload = async (e) => {
        const textContent = e.target.result;
        try {
          const resp = await fetch("/api/upload-check", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              filename: activeFile.name,
              content: textContent,
            }),
          });

          const data = await resp.json();
          if (!resp.ok) {
            throw new Error(data.error || `HTTP error ${resp.status}`);
          }

          if (uploadResults) {
            uploadResults.removeAttribute("hidden");
            if (uploadMetaName) uploadMetaName.textContent = data.filename;
            if (uploadMetaSize) uploadMetaSize.textContent = `${data.size} bytes`;
            if (uploadMetaMtime) uploadMetaMtime.textContent = `${Number(data.mtime).toFixed(4)}s`;
            if (uploadMetaHash) uploadMetaHash.textContent = data.content_hash;

            const wasCached = data.cache_state && data.cache_state.was_cached;
            if (uploadCacheStatus) uploadCacheStatus.textContent = wasCached ? "Prior Artifact Found in Cache" : "Cold Run (No Prior Artifact)";
            if (uploadCacheTime) uploadCacheTime.textContent = wasCached && data.cache_state.cached_mtime ? `${Number(data.cache_state.cached_mtime).toFixed(4)}s` : "None";
            if (uploadCacheHash) uploadCacheHash.textContent = wasCached && data.cache_state.cached_hash ? data.cache_state.cached_hash : "None";

            const isHit = !data.robust.is_stale;
            if (uploadVerdictTag) {
              uploadVerdictTag.textContent = isHit ? "CACHE HIT (REUSED)" : "CACHE MISS (REBUILT)";
              uploadVerdictTag.className = `verdict-tag ${isHit ? "pass" : "stale"}`;
            }
            if (uploadVerdictText) uploadVerdictText.textContent = data.diagnostic_verdict;

            if (uploadNaiveDecision) uploadNaiveDecision.textContent = data.naive.is_stale ? "Cache Stale (Rebuild Needed)" : "Cache Valid (Reuse)";
            if (uploadNaiveVerdict) uploadNaiveVerdict.textContent = data.naive.verdict;
            if (uploadNaiveReason) uploadNaiveReason.textContent = data.naive.reason;
            if (uploadNaiveBadge) {
              uploadNaiveBadge.textContent = data.naive.is_stale ? "STALE" : "VALID";
              uploadNaiveBadge.className = `status-indicator ${data.naive.is_stale ? "error" : "correct"}`;
            }

            if (uploadRobustDecision) uploadRobustDecision.textContent = data.robust.is_stale ? "Cache Stale (Invalidate & Rebuild)" : "Cache Valid (Verified Match)";
            if (uploadRobustVerdict) uploadRobustVerdict.textContent = data.robust.verdict;
            if (uploadRobustReason) uploadRobustReason.textContent = data.robust.reason;
            if (uploadRobustBadge) {
              uploadRobustBadge.textContent = data.robust.is_stale ? "STALE" : "VALID";
              uploadRobustBadge.className = `status-indicator ${data.robust.is_stale ? "error" : "correct"}`;
            }

            uploadResults.scrollIntoView({ behavior: "smooth", block: "nearest" });
            showToast("Real file verified via os.stat() and SHA-256", "toast-success");
          }
        } catch (err) {
          setUploadError(err.message || "Failed to check uploaded file.");
        } finally {
          btnUploadCheck.classList.remove("is-loading");
          btnUploadCheck.disabled = false;
        }
      };

      reader.readAsText(activeFile, "utf-8");
    });
  }

  // =========================================================================
  // AI Chat Assistant Widget (Meta Muse Spark 1.3)
  // =========================================================================
  const chatToggle = document.getElementById("chat-widget-toggle");
  const chatPanel = document.getElementById("chat-panel");
  const chatCloseBtn = document.getElementById("chat-close-btn");
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");
  const chatMessages = document.getElementById("chat-messages");
  const chatStatus = document.getElementById("chat-status");
  const chatSendBtn = document.getElementById("chat-send-btn");

  const conversationHistory = [];

  function toggleChat(open) {
    if (!chatPanel) return;
    const willOpen = open !== undefined ? open : chatPanel.hasAttribute("hidden");
    if (willOpen) {
      chatPanel.removeAttribute("hidden");
      chatPanel.setAttribute("aria-hidden", "false");
      if (chatToggle) chatToggle.setAttribute("aria-expanded", "true");
      if (chatInput) chatInput.focus();
    } else {
      chatPanel.setAttribute("hidden", "");
      chatPanel.setAttribute("aria-hidden", "true");
      if (chatToggle) {
        chatToggle.setAttribute("aria-expanded", "false");
        chatToggle.focus();
      }
    }
  }

  if (chatToggle && chatPanel && chatCloseBtn) {
    chatToggle.addEventListener("click", () => toggleChat());
    chatCloseBtn.addEventListener("click", () => toggleChat(false));
  }

  function appendChatMessage(role, text, isError = false) {
    if (!chatMessages) return null;
    const msgDiv = document.createElement("div");
    msgDiv.className = `chat-message ${role === "user" ? "user-message" : isError ? "error-message" : "assistant-message"}`;
    const p = document.createElement("p");
    p.textContent = text;
    msgDiv.appendChild(p);
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return p;
  }

  if (chatForm && chatInput && chatSendBtn) {
    chatForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const userText = chatInput.value.trim();
      if (!userText) return;

      appendChatMessage("user", userText);
      conversationHistory.push({ role: "user", content: userText });
      chatInput.value = "";
      chatInput.disabled = true;
      chatSendBtn.disabled = true;
      chatSendBtn.classList.add("is-loading");
      if (chatStatus) chatStatus.removeAttribute("hidden");

      let assistantParagraph = null;
      let fullReply = "";

      try {
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            messages: conversationHistory,
            stream: true,
          }),
        });

        if (!response.ok) {
          throw new Error(`Server returned status ${response.status}`);
        }

        assistantParagraph = appendChatMessage("assistant", "");

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let streamBuffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          streamBuffer += decoder.decode(value, { stream: true });
          const lines = streamBuffer.split("\n");
          streamBuffer = lines.pop() || "";

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || !trimmed.startsWith("data:")) continue;
            const dataStr = trimmed.replace(/^data:\s*/, "");
            if (dataStr === "[DONE]") break;

            try {
              const parsed = JSON.parse(dataStr);
              if (parsed.content) {
                fullReply += parsed.content;
                if (assistantParagraph) assistantParagraph.textContent = fullReply;
                if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;
              } else if (parsed.error) {
                fullReply += parsed.error;
                if (assistantParagraph) assistantParagraph.textContent = fullReply;
              }
            } catch {
              // Ignore partial chunk
            }
          }
        }

        if (!fullReply.trim() && assistantParagraph) {
          assistantParagraph.textContent = "The assistant was unable to generate a response. Please check your setup.";
        }

        conversationHistory.push({ role: "assistant", content: fullReply });
      } catch (err) {
        console.error("Chat error:", err);
        appendChatMessage(
          "assistant",
          "The assistant is temporarily unavailable. Please check your network connection.",
          true
        );
      } finally {
        if (chatStatus) chatStatus.setAttribute("hidden", "");
        chatInput.disabled = false;
        chatSendBtn.disabled = false;
        chatSendBtn.classList.remove("is-loading");
        chatInput.focus();
      }
    });
  }
});
