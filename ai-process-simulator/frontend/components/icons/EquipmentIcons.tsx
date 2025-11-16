import React from 'react';
import { EquipmentType } from '../../types';

const ReactorIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => (
  <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
    <path d="M12 52a20 20 0 0140 0" />
    <path d="M12 52V20h40v32" />
    <path d="M32 20v-8m-8-4h16" />
    <path d="M32 20v24" />
    <path d="M24 44l16-8m-16 0l16 8" />
  </svg>
);

const DistillationColumnIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => (
  <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
    <path d="M20 56a12 4 0 1024 0a12 4 0 10-24 0z" />
    <path d="M20 8a12 4 0 1024 0a12 4 0 10-24 0z" />
    <path d="M20 12v44M44 12v44" />
    <path d="M20 24h24m-24 16h24" />
  </svg>
);

const TankIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => (
  <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
    <path d="M16 56a16 4 0 1032 0a16 4 0 10-32 0z" />
    <path d="M16 12v44M48 12v44" />
    <path d="M16 12a16 4 0 1032 0a16 4 0 10-32 0z" />
  </svg>
);

const PumpIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => (
  <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
    <circle cx="32" cy="32" r="16" />
    <path d="M16 32H4m44 0h-8" />
    <path d="M24 24l16 16" />
    <path d="M32 16V4l8 8-8-8" />
  </svg>
);

const HeatExchangerIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => (
  <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
    <circle cx="32" cy="32" r="20" />
    <path d="M12 32h40" />
    <path d="M22 22l-8-8m24 0l8-8" />
    <path d="M22 42l-8 8m24 0l8 8" />
    <path d="M32 12V4m0 56v-8" />
  </svg>
);

const MixerIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => (
    <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
        <circle cx="32" cy="32" r="20" />
        <path d="M12 24l40 16m-40 0l40-16" />
    </svg>
);

const StreamIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => (
  <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="3" {...props}>
    <path d="M8 32h40" />
    <path d="M38 22l10 10-10 10" />
  </svg>
);

const SplitterIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => (
    <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
        <circle cx="32" cy="32" r="12" />
        <path d="M20 32H4" />
        <path d="M44 32h16l-8-8m8 8l-8 8" />
        <path d="M38 22l8-8" />
        <path d="M38 42l8 8" />
    </svg>
);

const HeaterIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => (
    <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
        <rect x="12" y="16" width="40" height="32" rx="4" />
        <path d="M4 32h8m40 0h8" />
        <path d="M28 24v16m8-16v16m-12-8h16" />
    </svg>
);

const CoolerIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => (
    <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
        <rect x="12" y="16" width="40" height="32" rx="4" />
        <path d="M4 32h8m40 0h8" />
        <circle cx="32" cy="32" r="6" />
        <path d="M32 26v-4m0 20v-4m-6-6h-4m20 0h-4m-9-9l-3-3m6 12l-3-3m-3 3l3-3m-6-6l3 3" />
    </svg>
);

const CompressorIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => (
    <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
        <path d="M12 20h40v24H12z" />
        <path d="M12 20L4 12v40l8-8m40-16h8" />
    </svg>
);

const ExpanderIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => (
    <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
        <path d="M12 16h40v32H12z" />
        <path d="M12 32H4m56 0l-8-8v16l8-8" />
    </svg>
);

const FlashIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => (
    <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
        <path d="M20 56v-48h24v48z" />
        <path d="M4 32h16m24-24v-4m0 48v4" />
    </svg>
);

interface EquipmentIconProps extends React.SVGProps<SVGSVGElement> {
  type: EquipmentType;
}

export const EquipmentIcon: React.FC<EquipmentIconProps> = ({ type, ...props }) => {
  switch (type) {
    case EquipmentType.Feed: return <StreamIcon {...props} />;
    case EquipmentType.Product: return <StreamIcon {...props} />;
    case EquipmentType.Tank: return <TankIcon {...props} />;
    case EquipmentType.Pump: return <PumpIcon {...props} />;
    case EquipmentType.Mixer: return <MixerIcon {...props} />;
    case EquipmentType.Splitter: return <SplitterIcon {...props} />;
    case EquipmentType.Heater: return <HeaterIcon {...props} />;
    case EquipmentType.Cooler: return <CoolerIcon {...props} />;
    case EquipmentType.HeatExchanger: return <HeatExchangerIcon {...props} />;
    case EquipmentType.Compressor: return <CompressorIcon {...props} />;
    case EquipmentType.Expander: return <ExpanderIcon {...props} />;
    case EquipmentType.Flash: return <FlashIcon {...props} />;
    case EquipmentType.DistillationColumn: return <DistillationColumnIcon {...props} />;
    case EquipmentType.Reactor: return <ReactorIcon {...props} />;
    default: return null;
  }
};
