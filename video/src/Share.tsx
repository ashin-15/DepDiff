import data from '../public/demo-data.json';
import {colors, Eyebrow, Frame, Heading, Mark, mono, Reveal} from './design';

export const Share = () => (
  <Frame chapter="03 / SHARE THE REVIEW" light>
    <div style={{display: 'flex', gap: 110, marginTop: 90}}>
      <div style={{width: 750}}>
        <Reveal><Eyebrow light>Bring evidence to the pull request.</Eyebrow></Reveal>
        <Reveal delay={0.1}><Heading>Make the<br />review portable.</Heading></Reveal>
        <Reveal delay={0.4} style={{fontSize: 32, lineHeight: 1.55, color: '#526052', marginTop: 34}}>Terminal for a quick read.<br />JSON for tooling.<br />Markdown for your review.</Reveal>
        <Reveal delay={0.8} style={{fontFamily: mono, fontSize: 21, padding: 24, marginTop: 32, background: '#e1e6d8', lineHeight: 1.7}}>
          <span style={{color: '#476332'}}># append to the comparison command</span><br />
          --format markdown<br />--output reports/review.md
        </Reveal>
      </div>
      <Reveal delay={0.5} style={{width: 810, background: '#fafaf4', border: '1px solid #c8cdc1', boxShadow: '12px 16px 0 #dce1d3', padding: '40px 42px', rotate: '1deg'}}>
        <div style={{fontFamily: mono, fontSize: 19, color: '#61715b', borderBottom: '1px solid #d2d8c9', paddingBottom: 24}}>reports/review.md / EXCERPT</div>
        <div style={{fontSize: 33, fontWeight: 600, lineHeight: 1.35, margin: '28px 0'}}>depdiff review: demo-package</div>
        <div style={{fontFamily: mono, fontSize: 24, lineHeight: 1.8}}>1.0.0 → 2.0.0<br /><span style={{background: '#fce0cf', padding: '4px 8px'}}>Verdict: {data.suspicious.report.assessment.verdict}</span></div>
        <div style={{marginTop: 28, fontSize: 26, fontWeight: 600}}>Capability changes</div>
        {data.suspicious.report.capabilities.diff.added.map((item) => (
          <div key={item.capability} style={{display: 'flex', justifyContent: 'space-between', fontFamily: mono, fontSize: 22, padding: '17px 0', borderBottom: '1px solid #d2d8c9'}}>
            <span>{item.capability}</span><span style={{color: '#476332'}}>ADDED</span>
          </div>
        ))}
        <div style={{fontSize: 20, color: '#61715b', lineHeight: 1.5, marginTop: 25}}>An explainable review recommendation,<br />not proof of maliciousness or safety.</div>
      </Reveal>
    </div>
  </Frame>
);

export const Closing = () => (
  <Frame chapter="REVIEW THE DELTA" light>
    <div style={{marginTop: 88, textAlign: 'center'}}>
      <Reveal><Mark size={66} light /></Reveal>
      <Reveal delay={0.1}><Heading style={{fontSize: 110, letterSpacing: -5, marginTop: 23}}>Review the delta.<br />Not just the version.</Heading></Reveal>
      <Reveal delay={0.4} style={{fontSize: 31, color: '#526052', marginTop: 26}}>Offline. Explainable. No package execution.</Reveal>
      <Reveal delay={0.6} style={{display: 'inline-block', fontFamily: mono, fontSize: 26, background: colors.ink, color: colors.mint, padding: '22px 36px', marginTop: 38}}>make demo-suspicious</Reveal>
      <Reveal delay={0.8} style={{fontSize: 23, color: '#526052', marginTop: 34}}>Static analysis supports human judgment. It does not prove safety.</Reveal>
    </div>
  </Frame>
);
