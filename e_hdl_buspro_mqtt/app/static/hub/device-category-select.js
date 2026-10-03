(() => {
  'use strict';
  const categories = [
    ['', 'Automatica'], ['light', 'Luce'], ['dimmer', 'Dimmer'],
    ['switch', 'Interruttore / relè'], ['cover', 'Oscurante'], ['shutter', 'Tapparella'],
    ['awning', 'Tenda'], ['gate', 'Cancello'], ['garage_door', 'Portone garage'],
    ['thermostat', 'Termostato'], ['fan', 'Ventilazione'],
    ['temperature_sensor', 'Sensore temperatura'], ['humidity_sensor', 'Sensore umidità'],
    ['illuminance_sensor', 'Sensore luminosità'], ['environment_sensor', 'Sensore ambientale'],
    ['presence', 'Presenza / movimento'], ['dry_contact', 'Contatto pulito'],
    ['binary_sensor', 'Sensore binario'], ['sensor', 'Sensore generico'], ['scenario', 'Scenario'],
  ];
  const hdlCategories = [
    ['Luci', 'Luce'], ['Switch', 'Interruttore / relè'], ['Curtain', 'Tenda'],
    ['Cover', 'Oscurante'], ['Sensori', 'Sensore generico'], ['BinarySensor', 'Sensore binario'],
    ['Climate', 'Termostato'], ['Fan', 'Ventilazione'], ['Temperature', 'Sensore temperatura'],
    ['Humidity', 'Sensore umidità'], ['Illuminance', 'Sensore luminosità'],
    ['Presence', 'Presenza / movimento'], ['DryContact', 'Contatto pulito'], ['Scenario', 'Scenario'],
  ];
  function upgrade(root = document) {
    root.querySelectorAll?.('input[name="device_class_override"], input[id$="_category"]').forEach(input => {
      const selected = String(input.value || '').trim(), select = document.createElement('select');
      select.name = input.name; select.id = input.id; select.title = 'Categoria dispositivo';
      const choices = input.name === 'device_class_override' ? [...categories] : [...hdlCategories];
      if (selected && !choices.some(([value]) => value === selected)) choices.push([selected, selected]);
      choices.forEach(([value, label]) => {
        const option = document.createElement('option'); option.value = value;
        option.textContent = value ? label : `Automatica: ${input.placeholder || 'categoria rilevata'}`;
        option.selected = value === selected; select.appendChild(option);
      });
      input.replaceWith(select);
    });
    root.querySelectorAll?.('form[data-bus-config]').forEach(form => {
      const input = form.querySelector('input[name="name_override"]');
      const row = form.closest('tr') || form.closest('.adminFutureCard');
      const title = row?.querySelector('td:first-child > b') || row?.querySelector(':scope > .flex > div > b');
      if (!input || !title) return;
      const original = title.dataset.originalName || title.textContent.trim();
      title.dataset.originalName = original;
      const custom = input.value.trim();
      title.textContent = custom || original;
      title.classList.toggle('busCustomName', Boolean(custom && custom !== original));
      let note = title.parentElement.querySelector(':scope > .busOriginalName');
      if (custom && custom !== original) {
        if (!note) { note = document.createElement('div'); note.className = 'muted busOriginalName'; title.after(note); }
        note.textContent = `Nome originale: ${original}`;
      } else note?.remove();
    });
  }
  const start = () => {
    if (!document.getElementById('busCustomNameStyle')) {
      const style = document.createElement('style'); style.id = 'busCustomNameStyle';
      style.textContent = '.busCustomName{color:#55dff5!important;text-shadow:0 0 12px rgba(85,223,245,.18)}';
      document.head.appendChild(style);
    }
    upgrade();
    document.addEventListener('econtrol:organization-changed', () => upgrade());
    new MutationObserver(records => records.forEach(record => record.addedNodes.forEach(node => {
      if (node.nodeType === Node.ELEMENT_NODE) upgrade(node);
    }))).observe(document.body, {childList: true, subtree: true});
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
