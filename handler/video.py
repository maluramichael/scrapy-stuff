import ffmpeg


def handle_video(absolute_file_path, doc):
    try:
        probe = ffmpeg.probe(absolute_file_path)
        streams = probe['streams']

        first_video_stream = next(
            (stream for stream in streams if stream['codec_type'] == 'video'),
            None
        )

        if first_video_stream is None:
            return {
                'error': str('No video stream found')
            }

        if 'duration' not in first_video_stream:
            return {
                'error': str('No duration found')
            }

        return {
            'streams': streams
        }
    except Exception as e:
        return {
            'error': str(e)
        }
