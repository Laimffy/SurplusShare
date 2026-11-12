/**
 * SurplusShare — Main JavaScript Application
 * Tagline: "Share More. Waste Less. Nourish Communities."
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Initialize Lucide Icons
  if (window.lucide) {
    window.lucide.createIcons();
  }

  // 2. Mobile Sidebar Toggle
  const sidebar = document.getElementById('sidebar');
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebarClose = document.getElementById('sidebarClose');
  const sidebarBackdrop = document.getElementById('sidebarBackdrop');

  function openSidebar() {
    if (sidebar) sidebar.classList.add('show');
    if (sidebarBackdrop) sidebarBackdrop.classList.add('show');
    document.body.style.overflow = 'hidden';
  }

  function closeSidebar() {
    if (sidebar) sidebar.classList.remove('show');
    if (sidebarBackdrop) sidebarBackdrop.classList.remove('show');
    document.body.style.overflow = '';
  }

  if (sidebarToggle) sidebarToggle.addEventListener('click', openSidebar);
  if (sidebarClose) sidebarClose.addEventListener('click', closeSidebar);
  if (sidebarBackdrop) sidebarBackdrop.addEventListener('click', closeSidebar);

  // 3. Expiry Countdown Real-time Updates
  function updateCountdowns() {
    const countdownElements = document.querySelectorAll('[data-expiry-timestamp]');
    const now = new Date();

    countdownElements.forEach((el) => {
      const expiryStr = el.getAttribute('data-expiry-timestamp');
      if (!expiryStr) return;

      const expiryDate = new Date(expiryStr);
      const diffMs = expiryDate - now;

      if (diffMs <= 0) {
        el.textContent = 'Expired';
        el.className = 'badge badge-expired';
      } else {
        const diffHrs = Math.floor(diffMs / (1000 * 60 * 60));
        const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

        if (diffHrs < 6) {
          el.textContent = `${diffHrs}h ${diffMins}m left`;
          el.className = 'badge badge-urgent';
        } else if (diffHrs < 24) {
          el.textContent = `${diffHrs}h left`;
          el.className = 'badge badge-warning';
        } else {
          const diffDays = Math.floor(diffHrs / 24);
          el.textContent = `${diffDays}d ${diffHrs % 24}h left`;
          el.className = 'badge badge-fresh';
        }
      }
    });
  }

  updateCountdowns();
  setInterval(updateCountdowns, 60000); // refresh every minute

  // 4. Client-side Search Filter for Tables / Cards
  const clientSearchInput = document.getElementById('clientSearchInput');
  if (clientSearchInput) {
    clientSearchInput.addEventListener('input', (e) => {
      const term = e.target.value.toLowerCase().trim();
      const searchableItems = document.querySelectorAll('.searchable-item');

      searchableItems.forEach((item) => {
        const text = item.textContent.toLowerCase();
        if (text.includes(term)) {
          item.style.display = '';
        } else {
          item.style.display = 'none';
        }
      });
    });
  }

  // 5. Toast Notifications
  window.showToast = function (message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `custom-toast toast-${type} animate-slide-in`;
    toast.innerHTML = `
      <div class="d-flex align-items-center justify-content-between">
        <span>${message}</span>
        <button type="button" class="btn-close ms-2" aria-label="Close" onclick="this.parentElement.parentElement.remove()"></button>
      </div>
    `;

    container.appendChild(toast);
    setTimeout(() => {
      toast.classList.add('fade-out');
      setTimeout(() => toast.remove(), 300);
    }, 4500);
  };

  // 6. Delete Confirmation Dialogs
  document.querySelectorAll('form[data-confirm]').forEach((form) => {
    form.addEventListener('submit', (e) => {
      const msg = form.getAttribute('data-confirm') || 'Are you sure you want to proceed?';
      if (!confirm(msg)) {
        e.preventDefault();
      }
    });
  });

  // 7. Benchmark Runner Interactive AJAX
  const runBenchmarkBtn = document.getElementById('runBenchmarkBtn');
  if (runBenchmarkBtn) {
    runBenchmarkBtn.addEventListener('click', async () => {
      const size = document.getElementById('datasetSizeSelect').value;
      const queries = document.getElementById('queryCountSelect').value;
      const trials = document.getElementById('trialsSelect').value;
      const loadingSpinner = document.getElementById('benchmarkLoading');
      const resultsContainer = document.getElementById('benchmarkResultsContainer');

      runBenchmarkBtn.disabled = true;
      if (loadingSpinner) loadingSpinner.classList.remove('d-none');
      if (resultsContainer) resultsContainer.classList.add('d-none');

      try {
        const response = await fetch('/api/benchmark/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ dataset_size: size, query_count: queries, trials: trials }),
        });

        const data = await response.json();
        if (data.status === 'success') {
          renderBenchmarkResults(data);
        } else {
          alert('Benchmark error: ' + (data.message || 'Unknown error'));
        }
      } catch (err) {
        console.error('Benchmark fetch failed:', err);
        alert('Benchmark request failed. Please check server log.');
      } finally {
        runBenchmarkBtn.disabled = false;
        if (loadingSpinner) loadingSpinner.classList.add('d-none');
        if (resultsContainer) resultsContainer.classList.remove('d-none');
      }
    });
  }

  function renderBenchmarkResults(data) {
    // Populate Table
    document.getElementById('benchDatasetSize').textContent = Number(data.dataset_size).toLocaleString();
    document.getElementById('benchQueryCount').textContent = Number(data.query_count).toLocaleString();
    document.getElementById('benchTrialsCount').textContent = data.trials_evaluated;

    document.getElementById('benchMergeSortTime').textContent = data.merge_sort.median_time_ms + ' ms';
    document.getElementById('benchLinearTotalTime').textContent = data.linear_search.total_time_ms + ' ms';
    document.getElementById('benchLinearPerQuery').textContent = data.linear_search.time_per_query_ms + ' ms';
    document.getElementById('benchBinaryTotalTime').textContent = data.binary_search.total_time_ms + ' ms';
    document.getElementById('benchBinaryPerQuery').textContent = data.binary_search.time_per_query_ms + ' ms';
    document.getElementById('benchSortedPipelineTime').textContent = data.sorted_pipeline.total_time_ms + ' ms';

    document.getElementById('benchSpeedup').textContent = data.analysis.speedup_per_query + 'x';
    const breakEvenEl = document.getElementById('benchBreakEven');
    if (data.analysis.break_even_query_count) {
      breakEvenEl.textContent = Number(data.analysis.break_even_query_count).toLocaleString() + ' queries';
    } else {
      breakEvenEl.textContent = 'N/A (Linear was faster or identical)';
    }

    const equivEl = document.getElementById('benchEquivalence');
    if (equivEl) {
      if (data.analysis.results_equivalent) {
        equivEl.innerHTML = '<span class="badge bg-success">100% Equivalent Results Verified</span>';
      } else {
        equivEl.innerHTML = '<span class="badge bg-danger">Discrepancy Detected</span>';
      }
    }

    // Render Benchmark Chart
    if (window.Chart) {
      renderBenchmarkChart(data);
    }
  }

  let benchmarkChartInstance = null;
  function renderBenchmarkChart(data) {
    const ctx = document.getElementById('benchmarkComparisonChart');
    if (!ctx) return;

    if (benchmarkChartInstance) {
      benchmarkChartInstance.destroy();
    }

    const labels = ['Linear Search Total', 'Binary Search Total (Sorted Data)', 'Merge Sort Pre-Processing', 'Combined Sort + Binary'];
    const times = [
      data.linear_search.total_time_ms,
      data.binary_search.total_time_ms,
      data.merge_sort.median_time_ms,
      data.sorted_pipeline.total_time_ms,
    ];

    benchmarkChartInstance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: `Runtime (ms) for ${Number(data.query_count).toLocaleString()} queries on N=${Number(data.dataset_size).toLocaleString()}`,
            data: times,
            backgroundColor: [
              '#C77850', // Terracotta
              '#6B8E4E', // Leaf Green
              '#D7A64B', // Harvest Gold
              '#285943', // Forest Green
            ],
            borderRadius: 6,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: true },
          tooltip: {
            callbacks: {
              label: (item) => `${item.parsed.y.toFixed(2)} ms`,
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            title: { display: true, text: 'Execution Time (Milliseconds)' },
          },
        },
      },
    });
  }
});
