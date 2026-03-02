import { useRef } from "react";
import { Electroview } from "electrobun/view";
import type { TeleMURPCSchema } from "../../shared/types";

let _instance: ReturnType<typeof Electroview.defineRPC<TeleMURPCSchema>> | null = null;

function getRPC() {
  if (!_instance) {
    _instance = Electroview.defineRPC<TeleMURPCSchema>({
      maxRequestTime: 300000,
      handlers: {
        requests: {},
        messages: {},
      },
    });
    new Electroview({ rpc: _instance });
  }
  return _instance;
}

export function useRPC() {
  const rpc = useRef(getRPC()).current;
  return rpc;
}

/** Convenience: call an RPC method and return the result */
export async function rpcRequest<
  M extends keyof TeleMURPCSchema["bun"]["requests"]
>(
  method: M,
  ...args: undefined extends TeleMURPCSchema["bun"]["requests"][M]["params"]
    ? [params?: TeleMURPCSchema["bun"]["requests"][M]["params"]]
    : [params: TeleMURPCSchema["bun"]["requests"][M]["params"]]
): Promise<TeleMURPCSchema["bun"]["requests"][M]["response"]> {
  const rpc = getRPC();
  return (rpc.request as any)(method, ...args);
}
