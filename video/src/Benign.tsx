import data from '../public/demo-data.json';
import {colors, Eyebrow, Frame, Heading, mono, Reveal, Terminal} from './design';

export const Benign = () => (
  <Frame chapter="A QUIETER UPGRADE">
    <div style={{display: 'flex', gap: 96, marginTop: 96}}>
      <div style={{width: 720}}>
        <Reveal><Eyebrow>Contrast with a benign fixture.</Eyebrow></Reveal>
        <Reveal delay={0.15}><Heading>No new signals.<br />Less to review.</Heading></Reveal>
        <Reveal delay={0.7} style={{fontSize: 32, lineHeight: 1.5, color: colors.muted, marginTop: 38}}>benign-package<br /><span style={{fontFamily: mono}}>1.0.0 → 1.1.0</span></Reveal>
        <Reveal delay={2.2} style={{marginTop: 52, paddingLeft: 24, borderLeft: `3px solid ${colors.mint}`, fontSize: 28, color: colors.muted, lineHeight: 1.5, maxWidth: 630}}>
          <span style={{color: colors.paper}}>ok is not a safety guarantee.</span><br />It means no new signals were found under the configured static rules.
        </Reveal>
      </div>
      <Reveal delay={0.45} style={{flex: 1}}>
        <Terminal title="terminal / benign comparison">
          <div style={{fontFamily: mono, fontSize: 21, lineHeight: 1.55, color: colors.muted, overflowWrap: 'anywhere'}}><span style={{color: colors.mint}}>$ </span>{data.benign.command}</div>
          <div style={{marginTop: 30, borderTop: `1px solid ${colors.line}`, paddingTop: 22}}>
            {data.benign.terminal.split('\n').slice(1, 12).map((line, index) => (
              <Reveal delay={1.1 + index * 0.06} key={index} style={{fontFamily: mono, fontSize: 25, lineHeight: 1.7, minHeight: 22, color: line.startsWith('Verdict:') ? colors.mint : colors.paper}}>{line}</Reveal>
            ))}
          </div>
        </Terminal>
      </Reveal>
    </div>
  </Frame>
);
