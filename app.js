(() => {
  const data = window.DASHBOARD_DATA;
  if (!data) {
    document.body.innerHTML = '<p style="padding:2rem;font-family:sans-serif">Data dashboard belum dibuat. Jalankan <code>python scripts/analyze.py</code>.</p>';
    return;
  }

  const $ = (selector) => document.querySelector(selector);
  const fmt = new Intl.NumberFormat('id-ID');
  const pct = (value) => `${Number(value).toLocaleString('id-ID', {minimumFractionDigits: 1, maximumFractionDigits: 1})}%`;
  const statusColor = {Prioritas: '#d65a5a', 'Perlu perhatian': '#f2b134', 'Relatif kuat': '#218c88'};
  const metrics = [
    ['persen_akreditasi_puncak', 'Akreditasi puncak', 'Perguruan tinggi berstatus Unggul/A'],
    ['persen_lulusan_stem', 'Lulusan STEM', 'Proporsi lulusan bidang STEM'],
    ['persen_dosen_senior', 'Dosen senior', 'Lektor Kepala dan Profesor'],
    ['persen_dosen_bersertifikasi', 'Sertifikasi dosen', 'Dosen berstatus sertifikasi']
  ];

  function renderPulse() {
    const n = data.national;
    const items = [
      [fmt.format(n.jumlah_pt), 'Perguruan tinggi'],
      [fmt.format(n.jumlah_lulusan), 'Lulusan dengan nilai valid'],
      [fmt.format(n.jumlah_dosen), 'Dosen dalam basis terpilih'],
      [fmt.format(n.province_count), 'Provinsi terpetakan']
    ];
    $('#national-pulse').innerHTML = items.map(([value, label]) => `<div class="pulse-item"><strong>${value}</strong><span>${label}</span></div>`).join('');
  }

  function shortName(name) {
    return name.replace('Nusa Tenggara', 'NT').replace('Kalimantan', 'Kalim.').replace('Sulawesi', 'Sul.').replace('Sumatera', 'Sum.').replace('Kepulauan', 'Kep.');
  }

  function renderRibbon() {
    const provinces = [...data.provinces].sort((a, b) => a.skor_kesiapan - b.skor_kesiapan);
    $('#readiness-ribbon').innerHTML = provinces.map((p) => `<button type="button" class="ribbon-bar" role="listitem" style="--score:${p.skor_kesiapan};--bar-color:${statusColor[p.prioritas]}" data-province="${p.provinsi}" data-short="${shortName(p.provinsi)}" data-score="${Number(p.skor_kesiapan).toLocaleString('id-ID', {maximumFractionDigits: 1})}" aria-label="${p.provinsi}: skor peringkat ${p.skor_kesiapan}, ${p.jumlah_gap} gap"></button>`).join('');
    document.querySelectorAll('.ribbon-bar').forEach((button) => button.addEventListener('click', () => {
      $('#province-select').value = button.dataset.province;
      updateProvince(button.dataset.province);
      $('#wilayah').scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
    }));
  }

  function narrative(p) {
    const below = metrics.filter(([key]) => p[key] < data.national[key]).map(([, label]) => label.toLowerCase());
    if (!below.length) return 'Keempat indikator berada di atas nilai nasional. Fokus berikutnya adalah menjaga kualitas data dan memahami variasi antarkabupaten/kota.';
    if (below.length === 1) return `Celah paling terlihat ada pada ${below[0]}. Intervensi dapat difokuskan tanpa mengabaikan indikator lain yang relatif kuat.`;
    return `${below.length} indikator berada di bawah nilai nasional: ${below.join(', ')}. Wilayah ini memerlukan diagnosis lintas-program sebelum menentukan intervensi.`;
  }

  function updateProvince(name) {
    const p = data.provinces.find((row) => row.provinsi === name) || data.provinces[0];
    $('#province-status').textContent = `${p.prioritas} · ${p.jumlah_gap} dari 4 gap`;
    $('#province-name').textContent = p.provinsi;
    $('#province-narrative').textContent = narrative(p);
    $('#province-score').textContent = Number(p.skor_kesiapan).toLocaleString('id-ID', {maximumFractionDigits: 1});
    document.querySelectorAll('.ribbon-bar').forEach((bar) => bar.classList.toggle('active', bar.dataset.province === p.provinsi));
    $('#metric-tracks').innerHTML = metrics.map(([key, label, note]) => {
      const value = p[key];
      const national = data.national[key];
      const delta = value - national;
      const direction = value < national ? 'is-gap' : 'is-above';
      return `<div class="metric-track"><div class="track-head"><span>${label}</span><strong>${pct(value)}</strong></div><div class="track-line"><span class="track-fill ${direction}" style="--value:${Math.min(value, 100)}%"></span><span class="track-national" style="--national:${Math.min(national, 100)}%" aria-label="Nilai nasional ${pct(national)}"></span></div><div class="track-note"><span>${note}</span><span>${delta >= 0 ? '+' : ''}${delta.toLocaleString('id-ID', {maximumFractionDigits: 1})} pp vs nasional</span></div></div>`;
    }).join('');
    const rankCards = [
      [p.lulusan_stem, 'Lulusan STEM', p.rank_lulusan_stem],
      [p.pt_akreditasi_puncak, 'PT akreditasi puncak', p.rank_pt_akreditasi_puncak],
      [p.dosen_senior, 'Dosen senior', p.rank_dosen_senior],
      [p.dosen_bersertifikasi, 'Dosen bersertifikasi', p.rank_dosen_bersertifikasi]
    ];
    $('#indicator-ranks').innerHTML = rankCards.map(([value, label, rank]) => `<article class="indicator-rank"><span>${label}</span><strong>${fmt.format(value)}</strong><small>Peringkat ${rank}/34 berdasarkan jumlah</small></article>`).join('');
    $('#province-volume').innerHTML = [
      [fmt.format(p.jumlah_pt), 'Perguruan tinggi'],
      [fmt.format(p.jumlah_lulusan), 'Lulusan'],
      [fmt.format(p.jumlah_dosen), 'Dosen dalam basis']
    ].map(([value, label]) => `<div class="volume-item"><span>${label}</span><strong>${value}</strong></div>`).join('');
  }

  function setupProvincePicker() {
    const select = $('#province-select');
    const provinces = [...data.provinces].sort((a, b) => a.provinsi.localeCompare(b.provinsi, 'id'));
    select.innerHTML = provinces.map((p) => `<option>${p.provinsi}</option>`).join('');
    select.addEventListener('change', () => updateProvince(select.value));
    const initial = [...data.provinces].sort((a, b) => b.jumlah_gap - a.jumlah_gap || a.skor_kesiapan - b.skor_kesiapan)[0];
    select.value = initial.provinsi;
    updateProvince(initial.provinsi);
  }

  function renderBarChart(target, rows, labelKey, valueKey, classKey = null, limit = 10) {
    const chosen = rows.slice(0, limit);
    const max = Math.max(...chosen.map((row) => row[valueKey]));
    $(target).innerHTML = chosen.map((row) => `<div class="bar-row ${classKey && row[classKey] === 'NON STEM' ? 'non-stem' : ''}"><span>${row[labelKey]}</span><div class="bar-track"><span class="bar-value" style="--width:${row[valueKey] / max * 100}%"></span></div><span class="bar-number">${fmt.format(row[valueKey])}</span></div>`).join('');
  }

  function renderLecturerQuadrant() {
    const rows = data.provinces;
    const xValues = rows.map((p) => p.persen_dosen_bersertifikasi);
    const yValues = rows.map((p) => p.persen_dosen_senior);
    const xMin = Math.max(0, Math.floor(Math.min(...xValues) - 3));
    const xMax = Math.min(100, Math.ceil(Math.max(...xValues) + 3));
    const yMin = 0;
    const yMax = Math.min(100, Math.ceil(Math.max(...yValues) + 3));
    const xPos = (value) => (value - xMin) / (xMax - xMin) * 100;
    const yPos = (value) => (value - yMin) / (yMax - yMin) * 100;
    const xNational = xPos(data.national.persen_dosen_bersertifikasi);
    const yNational = yPos(data.national.persen_dosen_senior);
    const maxDosen = Math.max(...rows.map((p) => p.jumlah_dosen));
    const points = rows.map((p) => {
      const size = 12 + Math.sqrt(p.jumlah_dosen / maxDosen) * 25;
      return `<button type="button" class="quadrant-point" style="--x:${xPos(p.persen_dosen_bersertifikasi)}%;--y:${yPos(p.persen_dosen_senior)}%;--size:${size}px;--point-color:${statusColor[p.prioritas]}" aria-label="${p.provinsi}: sertifikasi ${pct(p.persen_dosen_bersertifikasi)}, dosen senior ${pct(p.persen_dosen_senior)}, ${fmt.format(p.jumlah_dosen)} dosen"></button>`;
    }).join('');
    $('#lecturer-quadrant').innerHTML = `
      <span class="quadrant-zone zone-strong">Relatif kuat</span>
      <span class="quadrant-zone zone-career">Fokus kenaikan jabatan</span>
      <span class="quadrant-zone zone-cert">Fokus sertifikasi</span>
      <span class="quadrant-zone zone-priority">Prioritas kapasitas</span>
      <span class="quadrant-national vertical" style="--position:${xNational}%"></span>
      <span class="quadrant-national horizontal" style="--position:${yNational}%"></span>
      <span class="quadrant-national-label cert" style="--position:${xNational}%">Nasional ${pct(data.national.persen_dosen_bersertifikasi)}</span>
      <span class="quadrant-national-label senior" style="--position:${yNational}%">Nasional ${pct(data.national.persen_dosen_senior)}</span>
      <span class="quadrant-tick x-min">${xMin}%</span><span class="quadrant-tick x-max">${xMax}%</span>
      <span class="quadrant-tick y-min">${yMin}%</span><span class="quadrant-tick y-max">${yMax}%</span>
      ${points}`;

    const riau = rows.find((p) => p.provinsi === 'Riau');
    const kalsel = rows.find((p) => p.provinsi === 'Kalimantan Selatan');
    const diy = rows.find((p) => p.provinsi === 'D.I. Yogyakarta');
    $('#quadrant-insights').innerHTML = [
      [`Riau`, `Sertifikasi ${pct(riau.persen_dosen_bersertifikasi)}, tetapi dosen senior ${pct(riau.persen_dosen_senior)}—indikasi perlunya diagnosis kenaikan jabatan.`],
      [`Kalimantan Selatan`, `Dosen senior ${pct(kalsel.persen_dosen_senior)}, tetapi sertifikasi ${pct(kalsel.persen_dosen_bersertifikasi)}—kebutuhan intervensinya berbeda.`],
      [`D.I. Yogyakarta`, `Berada di atas nasional pada keduanya: ${pct(diy.persen_dosen_bersertifikasi)} tersertifikasi dan ${pct(diy.persen_dosen_senior)} senior.`]
    ].map(([label, body]) => `<article><strong>${label}</strong><p>${body}</p></article>`).join('');
  }

  function renderStructure() {
    renderBarChart('#accreditation-chart', data.accreditation, 'kategori', 'jumlah', null, 8);
    renderBarChart('#field-chart', data.graduate_fields, 'bidang', 'jumlah', 'kategori', 10);
    renderLecturerQuadrant();
  }

  function renderTable() {
    const query = $('#province-search').value.trim().toLowerCase();
    const status = $('#priority-filter').value;
    const rows = data.provinces
      .filter((p) => p.provinsi.toLowerCase().includes(query) && (status === 'all' || p.prioritas === status))
      .sort((a, b) => b.jumlah_gap - a.jumlah_gap || a.skor_kesiapan - b.skor_kesiapan || a.provinsi.localeCompare(b.provinsi, 'id'));
    const metricCell = (p, key) => {
      const isGap = p[key] < data.national[key];
      return `<td class="metric-cell ${isGap ? 'is-gap' : 'is-above'}" title="${isGap ? 'Di bawah' : 'Di atas atau sama dengan'} nilai nasional"><strong>${pct(p[key])}</strong><small>${isGap ? 'gap' : 'ok'}</small></td>`;
    };
    $('#priority-body').innerHTML = rows.length ? rows.map((p, index) => `<tr><td class="rank-cell">${index + 1}</td><td><strong>${p.provinsi}</strong></td><td><span class="status-dot" style="--status:${statusColor[p.prioritas]}"></span>${p.prioritas}</td><td class="gap-cell">${p.jumlah_gap}<span>/4</span></td><td class="score-cell">${Number(p.skor_kesiapan).toLocaleString('id-ID', {maximumFractionDigits: 1})}</td>${metricCell(p, 'persen_akreditasi_puncak')}${metricCell(p, 'persen_lulusan_stem')}${metricCell(p, 'persen_dosen_senior')}${metricCell(p, 'persen_dosen_bersertifikasi')}</tr>`).join('') : '<tr><td class="empty-row" colspan="9">Tidak ada provinsi yang cocok dengan filter.</td></tr>';
  }

  renderPulse();
  renderRibbon();
  setupProvincePicker();
  renderStructure();
  renderTable();
  $('#province-search').addEventListener('input', renderTable);
  $('#priority-filter').addEventListener('change', renderTable);
})();
