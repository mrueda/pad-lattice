import {MousePointer2} from 'lucide-react';

export interface Demonstration {
  pressed: boolean;
  approach: number;
}

export function DemoPointer({pressed, approach}: Demonstration) {
  return <span className={`demoPointer ${pressed ? 'pressed' : ''}`} aria-hidden="true"
    style={{transform: `translate(${(1 - approach) * 16}px, ${(1 - approach) * 20}px)`}}>
    <MousePointer2 />
  </span>;
}
