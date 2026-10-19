import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import data from '../public/demo-data.json';
import {clamp, colors, Eyebrow, Frame, Heading, mono, Pill, Reveal} from './design';

const descriptions: Record<string, {title: string; detail: string}> = {
  fs: {title: 'Filesystem access', detail: 'New file operation visible in source.'},
  'install-script': {title: 'Installation script', detail: 'New postinstall lifecycle hook.'},
  process: {title: 'Process execution', detail: 'New child-process call visible in source.'},
};

export const Changes = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const report = data.suspicious.report;
  return (
    <Frame chapter="02 / INSPECT THE DELTA">
      <Reveal style={{marginTop: 56}}><Eyebrow>What appeared in 2.0.0?</Eyebrow></Reveal>
      <Reveal delay={0.1}><Heading>Three new capabilities.</Heading></Reveal>
      <div style={{display: 'flex', gap: 92, marginTop: 54}}>
        <Reveal delay={0.5} style={{width: 530, borderTop: `1px solid ${colors.line}`, paddingTop: 24}}>
          <div style={{fontFamily: mono, fontSize: 23, color: colors.muted}}>DETERMINISTIC RISK SCORE</div>
          <div style={{fontSize: 190, lineHeight: 1.1, letterSpacing: -12, color: colors.coral}}>
            {Math.round(interpolate(frame, [0.7 * fps, 1.5 * fps], [0, report.assessment.score], clamp))}
          </div>
          <Pill color={colors.coral}>{report.assessment.verdict}</Pill>
          <div style={{fontSize: 30, lineHeight: 1.45, marginTop: 24, maxWidth: 460, color: colors.muted}}>A policy recommendation<br />for a human reviewer.</div>
        </Reveal>
        <div style={{flex: 1}}>
          {report.capabilities.diff.added.map((capability, index) => {
            const finding = capability.findings[0];
            const description = descriptions[capability.capability];
            return (
              <Reveal key={capability.capability} delay={0.75 + index * 0.9} style={{borderTop: `1px solid ${colors.line}`, padding: '22px 0 24px'}}>
                <div style={{display: 'flex', alignItems: 'center', gap: 22}}>
                  <span style={{fontFamily: mono, color: colors.mint, fontSize: 24}}>+</span>
                  <span style={{fontSize: 36, fontWeight: 500, flex: 1}}>{description.title}</span>
                  <Pill color={finding.severity === 'HIGH' ? colors.coral : colors.mint}>{finding.severity}</Pill>
                </div>
                <div style={{fontFamily: mono, fontSize: 21, color: colors.muted, margin: '12px 0 0 40px'}}>{finding.source_file}:{finding.line} / {capability.capability}</div>
              </Reveal>
            );
          })}
        </div>
      </div>
      <Reveal delay={3.5} style={{position: 'absolute', bottom: 112, left: 96, fontSize: 25, color: colors.muted}}>New static signals deserve review. They do not establish intent.</Reveal>
    </Frame>
  );
};
