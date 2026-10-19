"""Synthesize an original, deterministic ambient bed using only the stdlib."""

from array import array
from math import exp, pi, sin
from pathlib import Path
import struct
import sys
import wave


RATE = 24000
DURATION = 52


def make_audio(destination: Path) -> None:
    """Write stereo PCM without external sounds, services, or random inputs."""
    count = RATE * DURATION
    left = array("d", [0.0]) * count
    right = array("d", [0.0]) * count

    def tone(start: float, length: float, frequency: float, gain: float,
             pan: float = 0.0, pluck: bool = False) -> None:
        first = max(0, round(start * RATE))
        last = min(count, round((start + length) * RATE))
        for index in range(first, last):
            time = index / RATE - start
            if pluck:
                envelope = min(time / 0.008, 1.0) * exp(-time * 4.0)
            else:
                envelope = min(time / 1.2, 1.0, (length - time) / 1.6)
            phase = 2 * pi * frequency * time
            sample = (sin(phase) + 0.12 * sin(phase * 2)) * gain * envelope
            left[index] += sample * (1 - pan * 0.4)
            right[index] += sample * (1 + pan * 0.4)

    chords = (
        (110.0, 130.8128, 164.8138),
        (87.3071, 110.0, 130.8128),
        (130.8128, 164.8138, 195.9977),
        (97.9989, 123.4708, 146.8324),
    )
    for start in range(0, DURATION, 8):
        chord = chords[(start // 8) % len(chords)]
        for voice, frequency in enumerate(chord):
            tone(start, 9.5, frequency, 0.033, (voice - 1) * 0.65)
            tone(start, 9.5, frequency * 2.002, 0.008, (1 - voice) * 0.5)
        tone(start, 8, chord[0] / 2, 0.025)

    melody = (440.0, 659.2551, 523.2511, 587.3295, 440.0, 391.9954, 523.2511, 659.2551)
    for beat in range(DURATION * 2):
        tone(beat * 0.5, 1.25, melody[beat % len(melody)], 0.017,
             -0.65 if beat % 2 else 0.65, pluck=True)
    for cut in (6, 15, 25, 36, 43, 48):
        tone(cut, 0.7, 880, 0.024, pluck=True)
        tone(cut + 0.12, 0.6, 1320, 0.012, 0.3, pluck=True)

    destination.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destination), "wb") as output:
        output.setparams((2, 2, RATE, 0, "NONE", "not compressed"))
        block = bytearray()
        for index, (l_sample, r_sample) in enumerate(zip(left, right)):
            time = index / RATE
            fade = min(time / 1.5, 1.0, (DURATION - time) / 2.5)
            l_value = round(max(-1.0, min(1.0, l_sample * fade)) * 32767)
            r_value = round(max(-1.0, min(1.0, r_sample * fade)) * 32767)
            block.extend(struct.pack("<hh", l_value, r_value))
            if len(block) >= 65536:
                output.writeframesraw(block)
                block.clear()
        output.writeframesraw(block)


if __name__ == "__main__":
    target = (Path(sys.argv[1]) if len(sys.argv) > 1 else
              Path(__file__).resolve().parents[1] / "public" / "score.wav")
    make_audio(target)
    print("Generated original 52-second stereo score.")
