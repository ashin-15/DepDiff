import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import data from '../public/demo-data.json';
import {clamp, colors, Eyebrow, Frame, Heading, mono, Pill, Reveal} from './design';

const notes: Record<string, {title: string; explanation: string}> = {
  'install-script': {title: 'Runs during installation', explanation: 'A lifecycle hook adds behavior before normal package use.'},
  fs: {title: 'Can read a host file', explanation: 'The source contains a newly visible filesystem operation.'},
  process: {title: 'Can launch a process', explanation: 'The source contains a newly visible shell execution call.'},
};

export const Evidence = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const findings = data.suspicious.report.capabilities.new.findings;
  const ordered = ['install-script', 'fs', 'process'].map((name) => {
    const finding = findings.find((item) => item.capability === name);
    if (!finding) throw new Error(`Missing captured evidence: ${name}`);
    return finding;
  });
  return (
    <Frame chapter="02 / FOLLOW THE EVIDENCE">
      <Reveal style={{marginTop: 50}}><Eyebrow>Not just a score.</Eyebrow></Reveal>
      <Reveal delay={0.1}><Heading>See the exact source signal.</Heading></Reveal>
      <div style={{marginTop: 48}}>
        {ordered.map((finding, index) => {
          const active = interpolate(frame, [(0.6 + index * 2.2) * fps, (1.1 + index * 2.2) * fps], [0, 1], clamp);
          const note = notes[finding.capability];
          return (
            <Reveal key={finding.rule_id} delay={0.5 + index * 1.1} style={{display: 'flex', gap: 44, marginBottom: 20, minHeight: 157}}>
              <div style={{width: 1090, background: colors.panel, borderLeft: `3px solid ${colors.coral}`, padding: '22px 26px', opacity: 0.65 + active * 0.35}}>
                <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 19}}>
                  <span style={{fontFamily: mono, fontSize: 23, color: colors.muted}}>{finding.source_file}:<span style={{color: colors.coral}}>{finding.line}</span></span>
                  <Pill color={finding.severity === 'HIGH' ? colors.coral : colors.mint}>{finding.capability}</Pill>
                </div>
                <div style={{fontFamily: mono, fontSize: 28, color: colors.paper, whiteSpace: 'pre'}}>{finding.evidence}</div>
              </div>
              <div style={{flex: 1, paddingTop: 12}}>
                <div style={{fontSize: 29, fontWeight: 500, marginBottom: 12}}>{note.title}</div>
                <div style={{fontSize: 24, color: colors.muted, lineHeight: 1.45}}>{note.explanation}</div>
              </div>
            </Reveal>
          );
        })}
      </div>
      <Reveal delay={5.4} style={{position: 'absolute', left: 96, bottom: 105, fontFamily: mono, fontSize: 20, color: colors.muted}}>READ-ONLY REGEX SCANNING / SOURCE LOCATIONS / REVIEW REASONS</Reveal>
    </Frame>
  );
};
