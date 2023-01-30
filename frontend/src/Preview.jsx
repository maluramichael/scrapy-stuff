import { encode } from 'js-base64';
import styles     from './SearchScreen.module.scss';

export function Preview({ mime, _source, text }) {
    if (mime?.startsWith('image/') || mime?.startsWith('video/')) {
        const base64EncodedPath = encode(`${_source.path}/${_source.filename}`);

        return <div
            style={{ backgroundImage: `url(http://localhost:5000/images/${base64EncodedPath})` }}
            className={styles.preview}
        >
            <div>
                {text}
            </div>
        </div>;
    }

    return <div className={styles.preview}>
        <div>
            {text}
        </div>
    </div>;
}
