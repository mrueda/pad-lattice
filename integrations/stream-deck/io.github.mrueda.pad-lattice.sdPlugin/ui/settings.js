let socket, context, actionId;
let addressEdited = false;
const field = id => document.getElementById(id);
const send = message => { if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message)); };
const plugin = payload => send({event: 'sendToPlugin', action: actionId, context, payload});
function connectionState(connection) {
  const connected = connection === 'connected';
  const connecting = connection === 'connecting';
  field('status').dataset.connected = String(connected);
  field('pairForm').hidden = connected;
  field('pairFields').disabled = connecting || socket?.readyState !== WebSocket.OPEN;
  field('connectedAddress').hidden = !connected;
  field('disconnect').hidden = !connected && !connecting;
  field('disconnect').textContent = connecting ? 'Cancel' : 'Disconnect';
}
window.connectElgatoStreamDeckSocket = (port, uuid, registerEvent, info, actionInfo) => {
  const action = JSON.parse(actionInfo);
  context = uuid;
  actionId = action.action;
  field('sessionLabel').hidden = !actionId.endsWith('.session');
  field('slot').value = String(action.payload.settings.slot ?? 0);
  socket = new WebSocket(`ws://127.0.0.1:${Number(port)}`);
  socket.onopen = () => { send({event: registerEvent, uuid}); plugin({type: 'status'}); };
  socket.onmessage = event => {
    let message;
    try { message = JSON.parse(event.data); } catch { return; }
    if (message?.event === 'sendToPropertyInspector' && message.payload) {
      const payload = message.payload;
      if (typeof payload.status !== 'string' || typeof payload.address !== 'string') return;
      field('status').textContent = payload.status;
      if (!addressEdited) field('address').value = payload.address;
      field('connectedAddress').textContent = payload.address;
      field('error').textContent = typeof payload.error === 'string' ? payload.error : '';
      field('error').hidden = !field('error').textContent;
      connectionState(payload.connection);
    }
  };
  socket.onclose = () => {
    field('pin').value = '';
    field('status').textContent = 'Stream Deck disconnected';
    connectionState('unpaired');
  };
};
field('address').oninput = () => { addressEdited = true; };
field('slot').onchange = () => send({event: 'setSettings', context, payload: {slot: Number(field('slot').value)}});
field('pairForm').onsubmit = event => {
  event.preventDefault();
  addressEdited = false;
  field('error').hidden = true;
  plugin({type: 'pair', address: field('address').value.trim(), pin: field('pin').value});
  field('pin').value = '';
  connectionState('connecting');
};
field('disconnect').onclick = () => plugin({type: 'disconnect'});
