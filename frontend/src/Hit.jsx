import styles         from './SearchScreen.module.scss';
import classnames     from 'classnames';
import { Preview }    from './Preview.jsx';
import { Highlights } from './Highlights.jsx';

export const Hit = ({ _source, highlight, meta_data, ...rest }) => {
    return (
        <div
            className={classnames(styles.gridCell, {
                [styles.orange]: _source.mime?.startsWith('image/'), [styles.green]: _source.mime?.startsWith('video/'),
            })}
        >
            <Preview
                mime={_source?.mime}
                _source={_source}
                text={_source?.title || _source?.filename}
            />
            {/*{highlight && <Highlights highlights={highlight} />}*/}
        </div>
    );
};
