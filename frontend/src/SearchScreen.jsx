import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios        from 'axios';

import styles from './SearchScreen.module.css';

function Highlight({ children }) {
    return (
        <p className={styles.highlight}>
            {children}
        </p>
    );
}

function Hit({ _source, highlight, ...rest }) {
    return (
        <div>
            <h3>{_source.title}</h3>
            <i>{_source.date} / {_source.author} / {_source.category}</i>
            {highlight?.content?.map((text) => <Highlight>{text}</Highlight>)}
            <a target='_blank' href={_source.url}>Read more</a>
        </div>
    );
}

export default () => {
    const [searchQuery, setSearchQuery]          = useState('');
    const { isLoading, error, data, isFetching } = useQuery({
        queryKey: ['search', searchQuery],
        queryFn:  () => axios.get('http://127.0.0.1:5000/search', { params: { q: searchQuery } }).then(res => res),
        retry:    1,
    });

    return (
        <div>
            <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
            />
            {isLoading && <div>Loading...</div>}
            {error && <div>Error: {error.message}</div>}
            {isFetching && <div>Fetching...</div>}
            {data?.data?.hits?.hits?.map(hit => <Hit key={hit._id} {...hit} />)}
        </div>
    );
}
