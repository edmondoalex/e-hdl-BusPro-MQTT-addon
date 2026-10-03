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
  function upgrade(root = document) {
    root.querySelectorAll?.('input[name="device_class_override"]').forEach(input => {
      const selected = String(input.value || '').trim(), select = document.createElement('select');
      select.name = input.name; select.title = 'Categoria dispositivo';
      const choices = [...categories];
      if (selected && !choices.some(([value]) => value === selected)) choices.push([selected, selected]);
      choices.forEach(([value, label]) => {
        const option = document.createElement('option'); option.value = value;
        option.textContent = value ? `${label} (${value})` : `Automatica: ${input.placeholder || 'categoria rilevata'}`;
        option.selected = value === selected; select.appendChild(option);
      });
      input.replaceWith(select);
    });
  }
  const start = () => {
    upgrade();
    new MutationObserver(records => records.forEach(record => record.addedNodes.forEach(node => {
      if (node.nodeType === Node.ELEMENT_NODE) upgrade(node);
    }))).observe(document.body, {childList: true, subtree: true});
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
