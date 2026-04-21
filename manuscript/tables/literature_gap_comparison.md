# Author: Dr Diego Malpica MD

## Literature Gap Comparison

This table supports the Introduction gap statement. It is a narrative capability comparison based on published system descriptions and repository evidence, not a head-to-head benchmark study.

| System or paper | Primary scope | What it contributes | Main boundary relative to the planned manuscript | Citation |
| --- | --- | --- | --- | --- |
| Kubios HRV | Advanced HRV analysis software | Strong HRV preprocessing, time-domain and frequency-domain analysis, and widespread use in HRV research workflows. | Does not position itself as a task-calibrated aerospace operator-readiness framework combining fatigue, HRV, and task-specific human-factors weighting. | Tarvainen et al., 2014 |
| PhysioScripts | Extensible physiological signal processing platform | Open, modular processing of physiological data with editable workflows and a reusable scripting framework. | Focuses on signal processing infrastructure rather than an end-user decision-support platform that combines HRV, operational risk, and mission context. | Christie & Gianaros, 2013 |
| Fatmaxxer | Open-source mobile HRV exercise tool | Demonstrates low-cost, open-source DFA-alpha1 assessment during exercise and comparison against an established HRV package. | Narrow exercise-specific scope; not a broader longitudinal or operational platform. | Rogers et al., 2025 |
| OpenICE HRV cognitive-alert architecture | Context-aware real-time clinical interoperability | Shows that HRV can be embedded in a modular, open, real-time alerting architecture for clinical teams. | Oriented to operating-room cognitive alerts rather than aerospace medicine, circadian and fatigue modeling, or environmental overlays. | Arney et al., 2023 |
| FAST / SAFTE scheduling tool | Fatigue forecasting and schedule comparison | Validated fatigue modeling and schedule comparison for high-risk operations, with clear operational relevance. | Fatigue-centric by design; it does not provide standards-aligned HRV analytics, individualized physiological context, or integrated environmental monitoring in one open repository. | Hursh et al., 2004 |
| Wearable circadian physiology methods | Circadian estimation from widely used wearables | Demonstrates scalable inference of circadian physiology from consumer wearable data. | Focuses on circadian characterization rather than task-calibrated readiness fusion spanning fatigue, HRV, and human-factors demand profiles. | Bowman et al., 2021 |
| AI-edge multimodal wearable platform | Multimodal physiological signal monitoring | Illustrates an embedded multimodal physiological monitoring platform for wearable sensing. | Prioritizes multimodal sensing and edge AI, not transparent clinical-operational workflows, aerospace decision support, or integrated HRV plus fatigue governance. | Yang et al., 2020 |
| Operational Performance Indicator (planned manuscript) | Task-calibrated readiness framework with open reference implementation | Integrates SAFTE-style fatigue effectiveness, HRV-derived autonomic markers, MRT-derived task weighting, and UAS-specific vigilance/latency terms across manned-aviation and UAS categories. | Must remain explicitly bounded to methodology, reference implementation, and illustrative demonstration pending field calibration and external benchmarking. | Repository evidence + manuscript |

## Distilled gap statement

1. Existing HRV-focused tools are strong on signal analysis, but they generally stop short of task-calibrated readiness fusion.
2. Fatigue and circadian tools provide schedule and phase insights, but they do not typically integrate individualized HRV analytics and explicit per-task human-factors weighting in the same open framework.
3. Context-aware clinical or wearable monitoring systems demonstrate modular real-time architectures, but they are not usually built as audit-friendly aerospace operator-readiness frameworks spanning both manned aviation and UAS roles.
4. The manuscript can therefore justify a gap around task-calibrated composite readiness, explicit UAS vigilance/latency modeling, open reference implementation, and auditability rather than around any single algorithm alone.

## References

Arney, D., Zhang, Y., Kennedy-Metz, L. R., Dias, R. D., Goldman, J. M., & Zenati, M. A. (2023). An open-source, interoperable architecture for generating real-time surgical team cognitive alerts from heart-rate variability monitoring. *Sensors, 23*(8), 3890. <https://doi.org/10.3390/s23083890>

Bowman, C., Huang, Y., Walch, O. J., Fang, Y., Frank, E., Tyler, J., Mayer, C., Stockbridge, C., Goldstein, C., Sen, S., & Forger, D. B. (2021). A method for characterizing daily physiology from widely used wearables. *Cell Reports Methods, 1*(4), 100058. <https://doi.org/10.1016/j.crmeth.2021.100058>

Christie, I. C., & Gianaros, P. J. (2013). PhysioScripts: An extensible, open source platform for the processing of physiological data. *Behavior Research Methods, 45*(1), 125-131. <https://doi.org/10.3758/s13428-012-0233-x>

Hursh, S. R., Balkin, T. J., Miller, J. C., & Eddy, D. R. (2004). The Fatigue Avoidance Scheduling Tool: Modeling to minimize the effects of fatigue on cognitive performance. *SAE Technical Paper Series*. <https://doi.org/10.4271/2004-01-2151>

Rogers, B., Murias, J. M., & Fleitas-Paniagua, P. R. (2025). Validity of an open-source mobile app to measure fractal correlation properties of heart rate variability during exercise. *European Journal of Applied Physiology*. <https://doi.org/10.1007/s00421-025-06037-0>

Tarvainen, M. P., Niskanen, J.-P., Lipponen, J. A., Ranta-aho, P. O., & Karjalainen, P. A. (2014). Kubios HRV - Heart rate variability analysis software. *Computer Methods and Programs in Biomedicine, 113*(1), 210-220. <https://doi.org/10.1016/j.cmpb.2013.07.024>

Yang, C.-J., Fahier, N., He, C.-Y., Li, W.-C., & Fang, W.-C. (2020). An AI-edge platform with multimodal wearable physiological signals monitoring sensors for affective computing applications. In *2020 IEEE International Symposium on Circuits and Systems* (pp. 1-5). IEEE. <https://doi.org/10.1109/ISCAS45731.2020.9180909>
