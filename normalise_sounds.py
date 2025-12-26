from pathlib import Path

import subprocess
import shutil

DIRECTORY = Path("./src/assets/sounds/")

LOUDNESS_RANGE = 11.0
TARGET_LUFS = -14.0
TRUE_PEAK = -1.0

def normaliseWAV(wavFilePath: Path):
    tempPath = wavFilePath.with_suffix(".normalized.wav")
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(wavFilePath),
        "-af",
        f"loudnorm=I={TARGET_LUFS}:TP={TRUE_PEAK}:LRA={LOUDNESS_RANGE}",
        "-ar", "44100",
        "-ac", "1",
        "-sample_fmt", "s16",
        str(tempPath)
    ]

    subprocess.run(cmd, check=True)
    shutil.move(tempPath, wavFilePath)

def main():
    for wav in DIRECTORY.glob("*.wav"):
        print(f"normalising {wav.name}")
        normaliseWAV(wav)

    print("ez win")

if __name__ == "__main__":
    main()
