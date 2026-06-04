export type SimulatorPlatform = 'ios' | 'android';

export const SIMULATOR_PLATFORM_KEY = 'factsafe_sim_platform';

export function getSimulatorPlatform(): SimulatorPlatform {
  try {
    const v = localStorage.getItem(SIMULATOR_PLATFORM_KEY);
    if (v === 'android') return 'android';
  } catch {
    /* ignore */
  }
  return 'ios';
}

export function setSimulatorPlatform(p: SimulatorPlatform): void {
  try {
    localStorage.setItem(SIMULATOR_PLATFORM_KEY, p);
  } catch {
    /* ignore */
  }
}
