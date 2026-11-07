// Minimal ZIP writer: stored entries, UTF-8 names, no external dependencies.
function createZip(files) {
  const encoder = new TextEncoder();
  const chunks = [], directory = [];
  let offset = 0;
  const crc32 = bytes => {
    let crc = 0xffffffff;
    for (const byte of bytes) {
      crc ^= byte;
      for (let i = 0; i < 8; i++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
    }
    return (crc ^ 0xffffffff) >>> 0;
  };
  const header = size => ({bytes: new Uint8Array(size), view: null});
  for (const file of files) {
    const name = encoder.encode(file.name), data = file.data;
    const crc = crc32(data);
    const local = header(30); local.view = new DataView(local.bytes.buffer);
    const l = local.view;
    l.setUint32(0, 0x04034b50, true); l.setUint16(4, 20, true); l.setUint16(6, 0x800, true);
    l.setUint32(14, crc, true); l.setUint32(18, data.length, true); l.setUint32(22, data.length, true);
    l.setUint16(26, name.length, true);
    chunks.push(local.bytes, name, data);
    const central = header(46); central.view = new DataView(central.bytes.buffer);
    const c = central.view;
    c.setUint32(0, 0x02014b50, true); c.setUint16(4, 20, true); c.setUint16(6, 20, true); c.setUint16(8, 0x800, true);
    c.setUint32(16, crc, true); c.setUint32(20, data.length, true); c.setUint32(24, data.length, true);
    c.setUint16(28, name.length, true); c.setUint32(42, offset, true);
    directory.push(central.bytes, name);
    offset += 30 + name.length + data.length;
  }
  const centralSize = directory.reduce((sum, item) => sum + item.length, 0);
  const end = new Uint8Array(22), e = new DataView(end.buffer);
  e.setUint32(0, 0x06054b50, true); e.setUint16(8, files.length, true); e.setUint16(10, files.length, true);
  e.setUint32(12, centralSize, true); e.setUint32(16, offset, true);
  return new Blob([...chunks, ...directory, end], {type: 'application/zip'});
}
