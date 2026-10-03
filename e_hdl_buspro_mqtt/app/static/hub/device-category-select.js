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
  }
  const start = () => {
    upgrade();
    new MutationObserver(records => records.forEach(record => record.addedNodes.forEach(node => {
      if (node.nodeType === Node.ELEMENT_NODE) upgrade(node);
    }))).observe(document.body, {childList: true, subtree: true});
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
