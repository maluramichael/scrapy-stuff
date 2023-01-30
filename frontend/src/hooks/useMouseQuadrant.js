import { useMousePosition } from './useMousePosition';
import { useWindowSize }    from './useWindowSize';

export const useMouseQuadrant = (invert) => {
    const { x, y }          = useMousePosition();
    const { width, height } = useWindowSize();

    const quadrant = {
        x: x < width / 2 ? 'left' : 'right', y: y < height / 2 ? 'top' : 'bottom',
    };

    if (invert) {
        quadrant.x = quadrant.x === 'left' ? 'right' : 'left';
        quadrant.y = quadrant.y === 'top' ? 'bottom' : 'top';
    }

    return quadrant;
};
