async function loadPlugins() {
  const response = await fetch('../index.json');
  const data = await response.json();
  return data.plugins;
}

function renderPlugin(plugin) {
  const rawUrl = plugin.source_url;
  return `
    <div class="plugin-card" data-type="${plugin.type}" data-downloads="${plugin.downloads}" data-name="${plugin.name}" data-updated="${plugin.updated_at}">
      <div>
        <h3>${plugin.name}</h3>
        <span class="badge">${plugin.type.toUpperCase()}</span>
      </div>
      <p>${plugin.description || ''}</p>
      <small>by ${plugin.author} • v${plugin.version}</small>
      <small>Updated ${new Date(plugin.updated_at).toLocaleDateString()}</small>
      <div class="plugin-actions">
        <button data-url="${rawUrl}">Copy URL</button>
        <a href="${plugin.repository}" target="_blank" rel="noopener">View Code</a>
      </div>
    </div>
  `;
}

function bindCopyEvents(container) {
  container.querySelectorAll('button[data-url]').forEach((button) => {
    button.addEventListener('click', () => {
      navigator.clipboard.writeText(button.dataset.url || '').then(() => {
        button.textContent = 'Copied!';
        setTimeout(() => (button.textContent = 'Copy URL'), 1500);
      });
    });
  });
}

function filterPlugins(plugins) {
  const query = document.getElementById('search').value.toLowerCase();
  const type = document.getElementById('type-filter').value;
  const sortKey = document.getElementById('sort').value;

  return plugins
    .filter((plugin) => {
      const matchesQuery = plugin.name.toLowerCase().includes(query) || plugin.description.toLowerCase().includes(query);
      const matchesType = type === 'all' || plugin.type === type;
      return matchesQuery && matchesType;
    })
    .sort((a, b) => {
      if (sortKey === 'name') {
        return a.name.localeCompare(b.name);
      }
      if (sortKey === 'downloads') {
        return b.downloads - a.downloads;
      }
      return new Date(b.updated_at) - new Date(a.updated_at);
    });
}

async function init() {
  let plugins = await loadPlugins();
  const grid = document.getElementById('plugin-grid');
  const refresh = () => {
    const filtered = filterPlugins(plugins);
    grid.innerHTML = filtered.map(renderPlugin).join('');
    bindCopyEvents(grid);
  };

  document.getElementById('search').addEventListener('input', refresh);
  document.getElementById('type-filter').addEventListener('change', refresh);
  document.getElementById('sort').addEventListener('change', refresh);
  document.getElementById('refresh').addEventListener('click', async () => {
    plugins = await loadPlugins();
    refresh();
  });

  refresh();
}

init();
