/**
 * kutomoto.ui.js.app
 * Master Application Coordinator, Tab Navigation & Notification Manager
 * Copyrights reserved to 90Studio
 */

(function (window) {
  'use strict';

  class KutomotoApp {
    constructor() {
      this.activeTabId = 'tab-designer';
      this.initTabs();
      this.initHealthCheck();
      this.initSettings();
    }

    // ------------------------------------------------------------------------
    // TAB NAVIGATION
    // ------------------------------------------------------------------------
    initTabs() {
      const tabs = document.querySelectorAll('.nav-tab');
      tabs.forEach(tab => {
        tab.addEventListener('click', () => {
          const targetTabId = tab.getAttribute('data-tab');
          if (!targetTabId) return;
          this.switchTab(targetTabId);
        });
      });
    }

    switchTab(tabId) {
      this.activeTabId = tabId;

      // Update Nav Buttons
      document.querySelectorAll('.nav-tab').forEach(tab => {
        if (tab.getAttribute('data-tab') === tabId) {
          tab.classList.add('active');
        } else {
          tab.classList.remove('active');
        }
      });

      // Update Tab Panels
      document.querySelectorAll('.tab-panel').forEach(panel => {
        if (panel.id === tabId) {
          panel.classList.add('active');
        } else {
          panel.classList.remove('active');
        }
      });

      // Trigger canvas resize/render if switching to designer
      if (tabId === 'tab-designer' && window.KutomotoDesigner) {
        window.KutomotoDesigner.render();
      }
    }

    // ------------------------------------------------------------------------
    // HEALTH CHECK POLLING
    // ------------------------------------------------------------------------
    async initHealthCheck() {
      try {
        const resp = await fetch('/api/health');
        if (resp.ok) {
          const data = await resp.json();
          const indicator = document.getElementById('ws-connection-indicator');
          const label = document.getElementById('connection-status-label');
          if (indicator) indicator.classList.add('connected');
          if (label) label.textContent = 'Engine Ready';
          const footerState = document.getElementById('footer-engine-state');
          if (footerState) footerState.textContent = `Engine: ${data.runner_state || 'IDLE'}`;
        }
      } catch (err) {
        console.warn('Initial server health check note:', err);
      }
    }

    // ------------------------------------------------------------------------
    // SETTINGS MANAGEMENT
    // ------------------------------------------------------------------------
    initSettings() {
      const countdownInput = document.getElementById('setting-countdown-sec');
      const stepDelayInput = document.getElementById('setting-step-delay');
      const typingSpeedInput = document.getElementById('setting-typing-speed');

      if (countdownInput) {
        countdownInput.addEventListener('change', (e) => {
          const val = parseInt(e.target.value, 10) || 3;
          if (window.KutomotoRunner) {
            const wf = window.KutomotoRunner.getWorkflow();
            if (wf && wf.execution_settings) wf.execution_settings.countdown_seconds = val;
          }
        });
      }

      if (stepDelayInput) {
        stepDelayInput.addEventListener('change', (e) => {
          const val = parseInt(e.target.value, 10) || 120;
          if (window.KutomotoRunner) {
            const wf = window.KutomotoRunner.getWorkflow();
            if (wf && wf.execution_settings) wf.execution_settings.default_step_delay_ms = val;
          }
        });
      }

      if (typingSpeedInput) {
        typingSpeedInput.addEventListener('change', (e) => {
          const val = parseInt(e.target.value, 10) || 20;
          if (window.KutomotoRunner) {
            const wf = window.KutomotoRunner.getWorkflow();
            if (wf && wf.execution_settings) wf.execution_settings.typing_speed_ms = val;
          }
        });
      }
    }

    // ------------------------------------------------------------------------
    // GLOBAL TOAST NOTIFICATION
    // ------------------------------------------------------------------------
    showToast(message, type = 'info') {
      const hub = document.getElementById('toast-hub');
      if (!hub) return;

      const toast = document.createElement('div');
      toast.className = `toast toast-${type}`;
      toast.textContent = message;
      hub.appendChild(toast);

      setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s ease';
        setTimeout(() => toast.remove(), 300);
      }, 2800);
    }
  }

  // Initialize on DOMContentLoaded
  document.addEventListener('DOMContentLoaded', () => {
    window.KutomotoApp = new KutomotoApp();
  });

})(window);
