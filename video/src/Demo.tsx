import {Audio} from '@remotion/media';
import {linearTiming, TransitionSeries} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import {AbsoluteFill, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Benign} from './Benign';
import {Changes} from './Changes';
import {Compare} from './Compare';
import {colors, clamp} from './design';
import {Evidence} from './Evidence';
import {Opening} from './Opening';
import {Closing, Share} from './Share';
import './fonts.css';

export const Demo = () => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  return (
    <AbsoluteFill style={{background: colors.ink}}>
      <TransitionSeries>
        <TransitionSeries.Sequence name="The upgrade question" durationInFrames={6.4 * fps}><Opening /></TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 0.4 * fps})} />
        <TransitionSeries.Sequence name="Real CLI comparison" durationInFrames={9.4 * fps}><Compare /></TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 0.4 * fps})} />
        <TransitionSeries.Sequence name="New capabilities" durationInFrames={10.4 * fps}><Changes /></TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 0.4 * fps})} />
        <TransitionSeries.Sequence name="Source evidence" durationInFrames={11.4 * fps}><Evidence /></TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 0.4 * fps})} />
        <TransitionSeries.Sequence name="Benign comparison" durationInFrames={7.4 * fps}><Benign /></TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 0.4 * fps})} />
        <TransitionSeries.Sequence name="Export a Markdown review" durationInFrames={5.4 * fps}><Share /></TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 0.4 * fps})} />
        <TransitionSeries.Sequence name="Try DepDiff" durationInFrames={4 * fps}><Closing /></TransitionSeries.Sequence>
      </TransitionSeries>
      <Audio name="Original ambient score" src={staticFile('score.wav')} volume={0.6} />
      <div style={{position: 'absolute', bottom: 0, left: 0, height: 4, width: `${interpolate(frame, [0, durationInFrames - 1], [0, 100], clamp)}%`, background: colors.mint}} />
    </AbsoluteFill>
  );
};
