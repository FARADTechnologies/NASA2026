"""Assemble CDP screencast frames (frames.json + fNNNNN.jpg) into a constant-25-fps H.264 MP4 using imageio-ffmpeg's bundled ffmpeg.
Usage: python make_mp4.py <framesDir> <out.mp4> [trim_start_seconds]"""
import json, os, subprocess, sys
import imageio_ffmpeg
d, out = sys.argv[1], sys.argv[2]
meta = json.load(open(os.path.join(d, "frames.json")))
fr = meta["frames"]
lines = []
for i, f in enumerate(fr):
    dur = ((fr[i + 1]["t"] if i + 1 < len(fr) else f["t"] + 1000) - f["t"]) / 1000
    lines.append(f"file '{f['name']}'\nduration {max(dur, 0.001):.3f}")
lines.append(f"file '{fr[-1]['name']}'")
open(os.path.join(d, "list.txt"), "w").write("\n".join(lines) + "\n")
ff = imageio_ffmpeg.get_ffmpeg_exe()
trim = sys.argv[3] if len(sys.argv) > 3 else "0"
cmd = [ff, "-y", "-ss", trim, "-f", "concat", "-safe", "0", "-i", os.path.join(d, "list.txt"), "-vf", "fps=25,scale=1600:900:force_original_aspect_ratio=decrease,pad=1600:900:(ow-iw)/2:(oh-ih)/2",
       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", "-movflags", "+faststart", out]
subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("wrote", out, f"{os.path.getsize(out)/1e6:.1f} MB", f"{(fr[-1]['t']-fr[0]['t'])/1000:.1f} s")
