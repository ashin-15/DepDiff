import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const movie = fileURLToPath(new URL('../out/depdiff-demo.mp4', import.meta.url));
const info = JSON.parse(execFileSync('ffprobe', [
  '-v', 'error', '-show_streams', '-show_format', '-of', 'json', movie,
], {encoding: 'utf8', shell: false}));
const video = info.streams.find((stream) => stream.codec_type === 'video');
const audio = info.streams.find((stream) => stream.codec_type === 'audio');
assert.ok(video, 'Video stream is present');
assert.ok(audio, 'Audio stream is present');
assert.equal(video.codec_name, 'h264');
assert.equal(video.width, 1920);
assert.equal(video.height, 1080);
assert.equal(video.r_frame_rate, '30/1');
assert.equal(Number(video.nb_frames), 1560);
assert.equal(video.pix_fmt, 'yuv420p');
assert.equal(audio.codec_name, 'aac');
assert.equal(audio.channels, 2);
assert.ok(Math.abs(Number(info.format.duration) - 52) < 0.1);

// Decode every audio and video packet, rather than checking only the header.
execFileSync('ffmpeg', [
  '-nostdin', '-v', 'error', '-xerror', '-i', movie, '-map', '0', '-f', 'null', '-',
], {stdio: ['ignore', 'pipe', 'pipe'], shell: false});
console.log('Verified: 52 seconds, 1920x1080, 30 fps, 1560 H.264 frames, stereo AAC.');
console.log('Full audio/video decode passed.');
