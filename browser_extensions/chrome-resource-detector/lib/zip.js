(function () {
  'use strict';

  var CRC_TABLE = (function () {
    var table = new Uint32Array(256);
    for (var i = 0; i < 256; i++) {
      var c = i;
      for (var j = 0; j < 8; j++) {
        c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
      }
      table[i] = c;
    }
    return table;
  })();

  function crc32(data) {
    var crc = 0xFFFFFFFF;
    for (var i = 0; i < data.length; i++) {
      crc = CRC_TABLE[(crc ^ data[i]) & 0xFF] ^ (crc >>> 8);
    }
    return (crc ^ 0xFFFFFFFF) >>> 0;
  }

  function dosDateTime() {
    var now = new Date();
    var time = (now.getHours() << 11) | (now.getMinutes() << 5) | (now.getSeconds() >> 1);
    var date = ((now.getFullYear() - 1980) << 9) | ((now.getMonth() + 1) << 5) | now.getDate();
    return { time: time, date: date };
  }

  var ZipWriter = function () {
    this.files = [];
  };

  ZipWriter.prototype.addFile = function (filename, data) {
    var bytes = data instanceof Uint8Array ? data : new Uint8Array(data);
    this.files.push({ filename: filename, data: bytes });
    return this;
  };

  ZipWriter.prototype.generate = function () {
    var localHeaders = [];
    var centralHeaders = [];
    var offset = 0;
    var dt = dosDateTime();

    for (var i = 0; i < this.files.length; i++) {
      var file = this.files[i];
      var nameBytes = new TextEncoder().encode(file.filename);
      var crc = crc32(file.data);
      var size = file.data.length;
      var nameLen = nameBytes.length;

      var lh = new ArrayBuffer(30 + nameLen);
      var lhView = new DataView(lh);
      var lhArr = new Uint8Array(lh);
      lhView.setUint32(0, 0x04034b50, true);
      lhView.setUint16(4, 20, true);
      lhView.setUint16(6, 0x0800, true);
      lhView.setUint16(8, 0, true);
      lhView.setUint16(10, dt.time, true);
      lhView.setUint16(12, dt.date, true);
      lhView.setUint32(14, crc, true);
      lhView.setUint32(18, size, true);
      lhView.setUint32(22, size, true);
      lhView.setUint16(26, nameLen, true);
      lhView.setUint16(28, 0, true);
      lhArr.set(nameBytes, 30);

      var entryOffset = offset;
      localHeaders.push({ header: lhArr, data: file.data });
      offset += 30 + nameLen + size;

      var cd = new ArrayBuffer(46 + nameLen);
      var cdView = new DataView(cd);
      var cdArr = new Uint8Array(cd);
      cdView.setUint32(0, 0x02014b50, true);
      cdView.setUint16(4, 20, true);
      cdView.setUint16(6, 20, true);
      cdView.setUint16(8, 0x0800, true);
      cdView.setUint16(10, 0, true);
      cdView.setUint16(12, dt.time, true);
      cdView.setUint16(14, dt.date, true);
      cdView.setUint32(16, crc, true);
      cdView.setUint32(20, size, true);
      cdView.setUint32(24, size, true);
      cdView.setUint16(28, nameLen, true);
      cdView.setUint16(30, 0, true);
      cdView.setUint16(32, 0, true);
      cdView.setUint16(34, 0, true);
      cdView.setUint16(36, 0, true);
      cdView.setUint32(38, 0, true);
      cdView.setUint32(42, entryOffset, true);
      cdArr.set(nameBytes, 46);

      centralHeaders.push(cdArr);
    }

    var totalSize = 0;
    for (var i = 0; i < localHeaders.length; i++) {
      totalSize += localHeaders[i].header.length + localHeaders[i].data.length;
    }
    var cdOffset = totalSize;
    var cdSize = 0;
    for (var i = 0; i < centralHeaders.length; i++) {
      cdSize += centralHeaders[i].length;
    }
    totalSize += cdSize + 22;

    var zip = new Uint8Array(totalSize);
    var pos = 0;

    for (var i = 0; i < localHeaders.length; i++) {
      zip.set(localHeaders[i].header, pos); pos += localHeaders[i].header.length;
      zip.set(localHeaders[i].data, pos); pos += localHeaders[i].data.length;
    }

    for (var i = 0; i < centralHeaders.length; i++) {
      zip.set(centralHeaders[i], pos); pos += centralHeaders[i].length;
    }

    var eocdView = new DataView(zip.buffer, pos, 22);
    eocdView.setUint32(0, 0x06054b50, true);
    eocdView.setUint16(4, 0, true);
    eocdView.setUint16(6, 0, true);
    eocdView.setUint16(8, this.files.length, true);
    eocdView.setUint16(10, this.files.length, true);
    eocdView.setUint32(12, cdSize, true);
    eocdView.setUint32(16, cdOffset, true);
    eocdView.setUint16(20, 0, true);

    return zip;
  };

  self.ZipWriter = ZipWriter;
})();
