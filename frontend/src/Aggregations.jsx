import styles from './SearchScreen.module.scss';

export function Aggregations(props) {
    return (
        <div className={styles.aggregations}>
            <h3>{props.name}</h3>
            <ul>
                {props.data?.aggregations?.agg?.buckets?.map((bucket, index) => <li key={index}>
                        {bucket.key} ({bucket.doc_count})
                    </li>,
                )}
            </ul>
        </div>
    );
}
