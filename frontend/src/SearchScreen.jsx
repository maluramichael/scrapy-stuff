import { useState, useEffect, useRef } from 'react';
import { useInfiniteQuery }            from '@tanstack/react-query';
import { useInView }                   from 'react-intersection-observer';
import axios                           from 'axios';
import { encode }                      from 'js-base64';
import classnames                      from 'classnames';
import styles                          from './SearchScreen.module.scss';

function Highlights({ highlights }) {
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

function Preview({ mime, _source, text }) {
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

const useHover = (onHover, onLeave) => {
    const [value, setValue] = useState(false);

    const ref = useRef(null);

    const handleMouseOver = () => {
        setValue(true);
        onHover();
    };
    const handleMouseOut  = () => {
        setValue(false);
        onLeave();
    };

    useEffect(
        () => {
            const node = ref.current;
            if (node) {
                node.addEventListener('mouseover', handleMouseOver);
                node.addEventListener('mouseout', handleMouseOut);

                return () => {
                    node.removeEventListener('mouseover', handleMouseOver);
                    node.removeEventListener('mouseout', handleMouseOut);
                };
            }
        },
        [ref.current], // Recall only if ref changes
    );

    return [ref, value];
};

const Hit = ({ _source, highlight, meta_data, hover, ...rest }) => {
    const [hoverRef, isHovered] = useHover(() => hover(_source), () => hover(null));

    return (
        <div
            className={classnames(styles.gridCell, {
                [styles.orange]: _source.mime?.startsWith('image/'),
                [styles.green]:  _source.mime?.startsWith('video/'),
            })}
            ref={hoverRef}
        >
            <Preview
                mime={_source?.mime}
                _source={_source}
                text={_source?.title || _source?.filename}
            />
            <Highlights highlights={highlight} />
        </div>
    );
};

export const useMousePosition = () => {
    const [position, setPosition] = useState({ x: 0, y: 0 });

    useEffect(() => {
        const setFromEvent = (e) => setPosition({ x: e.clientX, y: e.clientY });
        window.addEventListener('mousemove', setFromEvent);

        return () => {
            window.removeEventListener('mousemove', setFromEvent);
        };
    }, []);

    return position;
};

const useWindowSize = () => {
    // Initialize state with undefined width/height so server and client renders match
    // Learn more here: https://joshwcomeau.com/react/the-perils-of-rehydration/
    const [windowSize, setWindowSize] = useState({
        width:  undefined,
        height: undefined,
    });

    useEffect(() => {
        // Handler to call on window resize
        function handleResize() {
            // Set window width/height to state
            setWindowSize({
                width:  window.innerWidth,
                height: window.innerHeight,
            });
        }

        // Add event listener
        window.addEventListener('resize', handleResize);

        // Call handler right away so state gets updated with initial window size
        handleResize();

        // Remove event listener on cleanup
        return () => window.removeEventListener('resize', handleResize);
    }, []); // Empty array ensures that effect is only run on mount

    return windowSize;
};

const useMouseQuadrant = (invert) => {
    const { x, y }          = useMousePosition();
    const { width, height } = useWindowSize();

    const quadrant = {
        x: x < width / 2 ? 'left' : 'right',
        y: y < height / 2 ? 'top' : 'bottom',
    };

    if (invert) {
        quadrant.x = quadrant.x === 'left' ? 'right' : 'left';
        quadrant.y = quadrant.y === 'top' ? 'bottom' : 'top';
    }

    return quadrant;
};

export default () => {
    const { inView }                    = useInView();
    const [searchQuery, setSearchQuery] = useState('');
    const quadrant                      = useMouseQuadrant(true);
    const [previewData, setPreviewData] = useState(null);
    const size                          = 100;
    const {
              data,
              error,
              isFetching,
              isLoading,
              fetchNextPage,
          }                             = useInfiniteQuery(
        ['projects', searchQuery],
        async ({ pageParam = 0 }) => {
            return await axios.get('http://127.0.0.1:5000/search', { params: { q: searchQuery, page: pageParam, size } });
        },
        {
            getPreviousPageParam: (firstPage) => {
                return firstPage.previousId ?? undefined;
            },
            getNextPageParam:     (lastPage) => {
                return lastPage.data.page + 1 ?? undefined;
            },
        },
    );

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

    const entries = data?.pages?.map(page => page.data?.hits?.hits || []).flat();

    return (
        <div className={styles.screen}>
            <div className={styles.inputContainer}>
                <input
                    placeholder={'Search...'}
                    className={styles.searchInput}
                    type="text"
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                />
            </div>
            {isLoading && <div>Loading...</div>}
            {error && <div>Error: {error.message}</div>}
            {isFetching && <div>Fetching...</div>}
            <div className={styles.grid}>
                {entries?.map(hit => <Hit
                    key={hit._id} {...hit}
                    hover={(data) => setPreviewData(data)}
                />)}
            </div>
            <div className={styles.overlay}>
                <div
                    className={classnames(styles.overlayContent, {
                        [styles.visible]: previewData,
                    })}
                    style={{ gridArea: `${quadrant.y}${quadrant.x}` }}
                >
                    <pre>
                        {JSON.stringify(previewData, null, 2)}
                    </pre>
                </div>
            </div>
        </div>
    );
}
