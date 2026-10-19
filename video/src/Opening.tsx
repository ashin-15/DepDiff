import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {clamp, colors, Eyebrow, Frame, Heading, mono, Reveal} from './design';

const Version = ({version, active = false}: {version: string; active?: boolean}) => (
  <div style={{width: 292, padding: '35px 30px', background: active ? colors.mint : colors.panel, color: active ? colors.ink : colors.paper, border: `1px solid ${active ? colors.mint : colors.line}`}}>
    <div style={{fontFamily: mono, fontSize: 20, marginBottom: 24, opacity: 0.7}}>{active ? 'AFTER' : 'BEFORE'}</div>
    <div style={{fontSize: 62, letterSpacing: -3}}>{version}</div>
  </div>
);

export const Opening = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <Frame chapter="THE UPGRADE QUESTION">
      <div style={{display: 'flex', marginTop: 112, gap: 48}}>
        <div style={{width: 900}}>
          <Reveal><Eyebrow>Look beyond the version number.</Eyebrow></Reveal>
          <Reveal delay={0.15}>
            <Heading style={{fontSize: 112, letterSpacing: -6}}>A version changed.<br />What else did?</Heading>
          </Reveal>
          <Reveal delay={0.6} style={{fontSize: 35, lineHeight: 1.5, color: colors.muted, marginTop: 38, maxWidth: 770}}>
            Compare npm upgrades.<br />See newly visible capabilities.<br />Review the evidence before merging.
          </Reveal>
        </div>
        <div style={{width: 760, paddingTop: 40}}>
          <Reveal delay={0.4} style={{fontFamily: mono, color: colors.muted, fontSize: 27, marginBottom: 30}}>demo-package</Reveal>
          <Reveal delay={0.7} style={{display: 'flex', alignItems: 'center', gap: 24}}>
            <Version version="1.0.0" />
            <span style={{fontSize: 46, color: colors.muted}}>→</span>
            <Version version="2.0.0" active />
          </Reveal>
          <div style={{height: 70, marginLeft: 520, borderLeft: `1px dashed ${colors.line}`, opacity: interpolate(frame, [1.2 * fps, 1.8 * fps], [0, 1], clamp)}} />
          <Reveal delay={1.5} style={{fontFamily: mono, fontSize: 25, padding: '23px 26px', border: `1px solid ${colors.line}`, lineHeight: 1.8}}>
            <span style={{color: colors.coral}}>+ postinstall</span><br />
            <span style={{color: colors.coral}}>+ filesystem access</span><br />
            <span style={{color: colors.coral}}>+ process execution</span>
          </Reveal>
        </div>
      </div>
      <Reveal delay={1.9} style={{position: 'absolute', bottom: 118, left: 96, display: 'flex', gap: 36, fontFamily: mono, fontSize: 22, color: colors.mint}}>
        <span>01 / COMPARE</span><span>02 / INSPECT</span><span>03 / SHARE</span>
      </Reveal>
    </Frame>
  );
};
