const fs = require('fs');
const { exec } = require('child_process');

module.exports = function format(value) {
  fs.readFileSync('/etc/hostname', 'utf8');
  exec('echo setup');
  return String(value).trim();
};
