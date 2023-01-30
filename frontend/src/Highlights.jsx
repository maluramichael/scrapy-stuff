import styles from './SearchScreen.module.scss';

export function Highlights({ highlights }) {
    const keys = Object.keys(highlights);

    if (keys.length === 0) {
        return null;
    }

    const renderedHighlights = [];

    for (const key of keys) {
        if (highlights[key].length > 0) {
            renderedHighlights.push(highlights[key].map((highlight, index) => <li
                key={index}
                className={styles.highlight}
            >
                <div dangerouslySetInnerHTML={{ __html: highlight }} />
            </li>));
        }
    }

    return (
        <p className={styles.highlight}>
            <ul>
                {renderedHighlights}
            </ul>
        </p>
    );
}
