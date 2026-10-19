import type {CSSProperties, ReactNode} from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

export const colors = {
  ink: '#101714',
  panel: '#17211c',
  line: '#344139',
  paper: '#f1f0e6',
  muted: '#a7b3a8',
  mint: '#c0f38a',
  coral: '#ff9c79',
};

export const mono = '"IBM Plex Mono", monospace';
export const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const ease = Easing.bezier(0.16, 1, 0.3, 1);

export const Reveal = ({children, delay = 0, style}: {
  children: ReactNode;
  delay?: number;
  style?: CSSProperties;
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <div style={{
      opacity: interpolate(frame, [delay * fps, (delay + 0.5) * fps], [0, 1], clamp),
      translate: `0 ${interpolate(frame, [delay * fps, (delay + 0.65) * fps], [28, 0], {...clamp, easing: ease})}px`,
      ...style,
    }}>
      {children}
    </div>
  );
};

export const Mark = ({size = 44, light = false}: {size?: number; light?: boolean}) => (
  <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
    <path d="M8 11H24V27H8V11Z" stroke={light ? colors.ink : colors.paper} strokeWidth="3" />
    <path d="M24 21H40V37H24V21Z" fill={light ? colors.ink : colors.mint} />
    <path d="M11 35H18M14.5 31.5V38.5" stroke={light ? colors.ink : colors.mint} strokeWidth="2" />
  </svg>
);

export const Frame = ({children, chapter, light = false}: {
  children: ReactNode;
  chapter: string;
  light?: boolean;
}) => (
  <AbsoluteFill style={{
    backgroundColor: light ? colors.paper : colors.ink,
    color: light ? colors.ink : colors.paper,
    fontFamily: 'Inter, sans-serif',
    padding: '60px 96px 86px',
  }}>
    <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: `1px solid ${light ? '#c8cdc1' : colors.line}`, paddingBottom: 22}}>
      <div style={{display: 'flex', alignItems: 'center', gap: 14}}>
        <Mark light={light} />
        <span style={{fontSize: 35, fontWeight: 700, letterSpacing: -1.5}}>depdiff</span>
      </div>
      <span style={{fontFamily: mono, fontSize: 21, letterSpacing: 2, color: light ? '#526052' : colors.muted}}>{chapter}</span>
    </div>
    {children}
    <div style={{position: 'absolute', bottom: 34, left: 96, right: 96, display: 'flex', justifyContent: 'space-between', fontFamily: mono, fontSize: 18, color: light ? '#526052' : colors.muted}}>
      <span>BEHAVIORAL DEPENDENCY REVIEW</span>
      <span>OFFLINE DEMO / SYNTHETIC FIXTURES</span>
    </div>
  </AbsoluteFill>
);

export const Eyebrow = ({children, light = false}: {children: ReactNode; light?: boolean}) => (
  <div style={{fontFamily: mono, fontSize: 23, letterSpacing: 2.8, textTransform: 'uppercase', color: light ? '#476332' : colors.mint, marginBottom: 24}}>{children}</div>
);

export const Heading = ({children, style}: {children: ReactNode; style?: CSSProperties}) => (
  <h1 style={{fontSize: 88, letterSpacing: -4.5, lineHeight: 1.08, fontWeight: 600, margin: 0, ...style}}>{children}</h1>
);

export const Pill = ({children, color = colors.mint}: {children: ReactNode; color?: string}) => (
  <span style={{display: 'inline-block', fontFamily: mono, fontSize: 22, color, border: `1px solid ${color}`, padding: '8px 14px', borderRadius: 4}}>{children}</span>
);

export const Terminal = ({title, children, style}: {title: string; children: ReactNode; style?: CSSProperties}) => (
  <div style={{background: '#121b16', border: `1px solid ${colors.line}`, borderRadius: 12, overflow: 'hidden', boxShadow: '0 24px 64px #00000025', ...style}}>
    <div style={{height: 56, background: '#1c2820', display: 'flex', alignItems: 'center', gap: 9, padding: '0 22px', color: colors.muted, fontFamily: mono, fontSize: 18}}>
      <span style={{width: 10, height: 10, background: '#718571', borderRadius: '50%'}} />
      <span style={{width: 10, height: 10, background: '#526552', borderRadius: '50%'}} />
      <span style={{width: 10, height: 10, background: '#3f5140', borderRadius: '50%'}} />
      <span style={{marginLeft: 14}}>{title}</span>
    </div>
    <div style={{padding: '30px 34px'}}>{children}</div>
  </div>
);
