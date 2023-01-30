import { useState }  from 'react';
import { useRef }    from 'react';
import { useEffect } from 'react';

export const useHover = (onHover, onLeave) => {
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

    useEffect(() => {
            const node = ref.current;
            if (node) {
                node.addEventListener('mouseover', handleMouseOver);
                node.addEventListener('mouseout', handleMouseOut);

                return () => {
                    node.removeEventListener('mouseover', handleMouseOver);
                    node.removeEventListener('mouseout', handleMouseOut);
                };
            }
        }, [ref.current], // Recall only if ref changes
    );

    return [ref, value];
};
