import { useState, useEffect, useRef } from 'react';
import { useInfiniteQuery }            from '@tanstack/react-query';
import { useQuery }                    from '@tanstack/react-query';
import { useInView }                   from 'react-intersection-observer';
import axios                           from 'axios';
import styles                          from './SearchScreen.module.scss';
import { Aggregations }                from './Aggregations.jsx';
import { Hit }                         from './Hit.jsx';
import { useMouseQuadrant }            from './hooks/useMouseQuadrant';

export default () => {
    const { inView }                    = useInView();
    const [searchQuery, setSearchQuery] = useState('');
    const [makeFilter, setMakeFilter]   = useState([]);
    const quadrant                      = useMouseQuadrant(true);
    const [previewData, setPreviewData] = useState(null);
    const size                          = 100;
    const {
              data: results,
              fetchNextPage,
          }                             = useInfiniteQuery(['projects', searchQuery], async ({ pageParam = 0 }) => {
        return await axios.get('http://127.0.0.1:5000/search', { params: { q: searchQuery, page: pageParam, size } });
    }, {
        getPreviousPageParam: (firstPage) => {
            return firstPage.previousId ?? undefined;
        }, getNextPageParam:  (lastPage) => {
            return lastPage.data.page + 1 ?? undefined;
        },
    });
    const { data: aggsMake }            = useQuery({
        queryKey: ['aggsMake', searchQuery], queryFn: async () => {
            return await axios.get('http://127.0.0.1:5000/aggs', { params: { name: 'Camera', q: searchQuery, field: 'meta_data.make.keyword' } });
        },
    });

    useEffect(() => {
        if (inView) {
            fetchNextPage();
        }
    }, [inView]);

    const handleScroll = () => {
        const bottom = Math.ceil(window.innerHeight + window.scrollY) >= document.documentElement.scrollHeight - 200;

        if (bottom) {
            fetchNextPage();
        }
    };

    useEffect(() => {
        window.addEventListener('scroll', handleScroll, {
            passive: true,
        });

        return () => {
            window.removeEventListener('scroll', handleScroll);
        };
    }, []);

    const entries = results?.pages?.map(page => page.data?.hits?.hits || []).flat();

    return (
        <div className={styles.screen}>
            <div className={styles.sidebar}>
                <div className={styles.inputContainer}>
                    <input
                        placeholder={'Search...'}
                        className={styles.searchInput}
                        type="text"
                        value={searchQuery}
                        onChange={e => setSearchQuery(e.target.value)}
                    />
                </div>
                <div className={styles.aggs}>
                    <Aggregations
                        name={'Camera'}
                        data={aggsMake?.data}
                        onChange={(value) => {
                            setMakeFilter([value]);
                        }}
                    />
                    <pre>
                        {JSON.stringify(makeFilter, null, 2)}
                    </pre>
                </div>
            </div>
            <div className={styles.results}>
                <div className={styles.grid}>
                    {entries?.map(hit => <Hit
                        key={hit._id} {...hit}
                        clicked={(data) => {
                            setPreviewData(data);
                        }}
                    />)}
                </div>
            </div>
        </div>
    );
}
