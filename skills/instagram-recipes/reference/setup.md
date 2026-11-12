# Setup

Python 3 and ffmpeg are required. yt-dlp and whisper are only needed for the
reels that have no written recipe, which is usually about half a collection. If
you skip them you still get a working book, with the rest listed as links to
watch yourself.

## macOS

```bash
brew install ffmpeg yt-dlp whisper-cpp
```

Then get a whisper model. The base English one is 142 MB and is plenty for
someone talking to a phone camera:

```bash
mkdir -p work/models
curl -L -o work/models/ggml-base.en.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin
```

`watch.sh` looks for it in `work/models/`, in `~/.cache/whisper/`, and in
Homebrew's share directory, or you can point at it with `--model`.

## Linux

```bash
sudo apt install -y ffmpeg python3-pip
pipx install yt-dlp     # or: python3 -m pip install --user yt-dlp
```

whisper.cpp is a short build:

```bash
git clone https://github.com/ggerganov/whisper.cpp && cd whisper.cpp
cmake -B build && cmake --build build -j --config Release
sudo cp build/bin/whisper-cli /usr/local/bin/
sh ./models/download-ggml-model.sh base.en
```

## If yt-dlp is broken

On macOS, Homebrew's yt-dlp sometimes fails with `No module named expat`,
because the Python it bundles was built without it. Don't fight the Homebrew
install. Make a venv with the system Python instead:

```bash
python3 -m venv work/venv
work/venv/bin/pip install -q yt-dlp
```

`watch.sh` checks `work/venv/bin/yt-dlp` if there is no yt-dlp on the PATH.

## Browsers

`watch.sh --browser` takes chrome, safari, firefox, brave, edge, chromium or
vivaldi, whichever you are signed in to Instagram with. Chrome is the default.
On macOS, Safari needs full disk access for the terminal, so Chrome is the
easier choice.

## Instead of local whisper

If you would rather pay per minute than install anything, you can transcribe
with a hosted speech-to-text API and write the result to `work/txt/<code>.txt`
yourself. Everything downstream reads that directory and does not care where
the text came from. Local whisper is free and runs about as fast as real time
on an Apple silicon CPU, so there is not much reason to.
