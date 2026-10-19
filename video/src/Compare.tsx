import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import data from '../public/demo-data.json';
import {clamp, colors, Eyebrow, Frame, Heading, mono, Reveal, Terminal} from './design';

export const Compare = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const command = data.suspicious.command.replace(' --fixtures-dir', ' \\\n  --fixtures-dir');
  const characters = Math.floor(interpolate(frame, [0.5 * fps, 2.5 * fps], [0, command.length], clamp));
  // These are verbatim lines from the real CLI, not a mock terminal response.
  const output = data.suspicious.terminal.split('\n').slice(0, 12);
  return (
    <Frame chapter="01 / COMPARE">
      <div style={{display: 'flex', gap: 82, marginTop: 74}}>
        <div style={{width: 450, paddingTop: 20}}>
          <Reveal><Eyebrow>One local command.</Eyebrow></Reveal>
          <Reveal delay={0.15}><Heading style={{fontSize: 83}}>Compare<br />before<br />you merge.</Heading></Reveal>
          <Reveal delay={1} style={{fontSize: 31, color: colors.muted, lineHeight: 1.5, marginTop: 32}}>
            Two versions in.<br />Explainable changes out.
          </Reveal>
          <Reveal delay={3.2} style={{marginTop: 50, borderLeft: `3px solid ${colors.mint}`, paddingLeft: 22, color: colors.muted, fontSize: 25, lineHeight: 1.6}}>
            Offline fixtures.<br />Read-only static analysis.<br />No package code executed.
          </Reveal>
        </div>
        <Reveal delay={0.35} style={{flex: 1}}>
          <Terminal title="terminal / repository root" style={{height: 682}}>
            <div style={{display: 'flex', gap: 18, minHeight: 108, fontFamily: mono, fontSize: 25, lineHeight: 1.6}}>
              <span style={{color: colors.mint}}>$</span>
              <span style={{whiteSpace: 'pre-wrap', overflowWrap: 'anywhere'}}>{command.slice(0, characters)}<span style={{color: colors.mint, opacity: frame < 2.6 * fps && Math.floor(frame / 12) % 2 === 0 ? 1 : 0}}>▌</span></span>
            </div>
            <div style={{height: 1, background: colors.line, margin: '12px 0 22px', opacity: interpolate(frame, [2.5 * fps, 2.8 * fps], [0, 1], clamp)}} />
            <div style={{fontFamily: mono, fontSize: 24, lineHeight: 1.55}}>
              {output.map((line, index) => (
                <div key={index} style={{
                  minHeight: 22,
                  whiteSpace: 'pre-wrap',
                  opacity: interpolate(frame, [(2.7 + index * 0.075) * fps, (2.9 + index * 0.075) * fps], [0, 1], clamp),
                  color: line.startsWith('Verdict:') ? colors.coral : line.startsWith('- ADDED:') ? colors.mint : colors.paper,
                }}>{line}</div>
              ))}
            </div>
          </Terminal>
          <Reveal delay={4.2} style={{marginTop: 23, fontFamily: mono, fontSize: 19, color: colors.muted}}>Actual CLI output, shown in an animated terminal.</Reveal>
        </Reveal>
      </div>
    </Frame>
  );
};
