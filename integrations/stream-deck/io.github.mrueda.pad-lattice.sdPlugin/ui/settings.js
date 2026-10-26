let socket, context, actionId;
const field = id => document.getElementById(id);
const send = message => { if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message)); };
const plugin = payload => send({event: 'sendToPlugin', action: actionId, context, payload});
window.connectElgatoStreamDeckSocket = (port, uuid, registerEvent, info, actionInfo) => {
  const action = JSON.parse(actionInfo);
  context = uuid;
  actionId = action.action;
  field('sessionLabel').hidden = !actionId.endsWith('.session');
  field('slot').value = String(action.payload.settings.slot ?? 0);
  socket = new WebSocket(`ws://127.0.0.1:${Number(port)}`);
  socket.onopen = () => { send({event: registerEvent, uuid}); plugin({type: 'status'}); };
  socket.onmessage = event => {
    const message = JSON.parse(event.data);
    if (message.event === 'sendToPropertyInspector') {
      field('status').textContent = message.payload.status;
      if (document.activeElement !== field('address')) field('address').value = message.payload.address;
    }
  };
  socket.onclose = () => { field('status').textContent = 'Stream Deck disconnected'; };
};
field('slot').onchange = () => send({event: 'setSettings', context, payload: {slot: Number(field('slot').value)}});
field('pairForm').onsubmit = event => {
  event.preventDefault();
  plugin({type: 'pair', address: field('address').value.trim(), pin: field('pin').value});
  field('pin').value = '';
};
field('disconnect').onclick = () => plugin({type: 'disconnect'});
