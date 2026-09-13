from workers.tasks.media_transcode import transcode_recording_to_hls

result = transcode_recording_to_hls.apply(
    args=("test-session-1", "/tmp/raw/test.mp4", "/tmp/hls_out")
).get()
print("RESULT:", result)
