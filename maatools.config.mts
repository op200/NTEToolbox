import type { FullConfig } from "@nekosu/maa-tools";

const config: FullConfig = {
   // @ts-expect-error
   cwd: import.meta.dirname,
   maaVersion: "latest",
   interfacePath: "assets/interface.jsonc",
   check: {
      override: {
         // 忽略 mpe-config 带来的报错
         // ignore warning caused by mpe-config
         // 'mpe-config': 'ignore'
      }
   }
};

export default config;
