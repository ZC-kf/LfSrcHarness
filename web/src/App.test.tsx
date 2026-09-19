import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

describe("LfSrcHarness console", () => {
  afterEach(cleanup);
  afterEach(() => { delete window.pywebview; });
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true,
      json: async () => [],
    })));
  });

  it("renders all operational navigation surfaces", async () => {
    render(<App />);

    expect(await screen.findByText("LfSrcHarness")).toBeInTheDocument();
    for (const label of ["总览", "任务", "运行", "事件", "证据", "报告", "审批", "模型", "节点", "设置"]) {
      expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
    }
    expect(screen.getByText("全局急停")).toBeInTheDocument();
  });

  it("saves a model provider without displaying its API key", async () => {
    const fetchMock = vi.fn(async (path: string, _init?: RequestInit) => ({
      ok: true,
      status: 200,
      json: async () => path === "/api/settings/providers" ? [] : {
        name: "deepseek", kind: "openai_compatible", base_url: "https://api.example.test/v1",
        model: "example-model", has_api_key: true,
      },
    }));
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "模型" }));
    fireEvent.change(screen.getByLabelText("配置名称"), { target: { value: "deepseek" } });
    fireEvent.change(screen.getByLabelText("接口地址"), { target: { value: "https://api.example.test/v1" } });
    fireEvent.change(screen.getByLabelText("模型名称"), { target: { value: "example-model" } });
    fireEvent.change(screen.getByLabelText("API 密钥（可选）"), { target: { value: "test-secret-key" } });
    fireEvent.click(screen.getByRole("button", { name: "保存模型配置" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/settings/providers/deepseek",
      expect.objectContaining({ method: "PUT" }),
    ));
    expect(screen.queryByText("test-secret-key")).not.toBeInTheDocument();
  });

  it("uses desktop bridge authorization without browser-stored tokens", async () => {
    const fetchMock = vi.fn(async (_path: string, _init?: RequestInit) => ({ ok: true, status: 200, json: async () => [] }));
    vi.stubGlobal("fetch", fetchMock);
    window.pywebview = { api: { get_token: async () => "desktop-session-token" } };
    render(<App />);

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      headers: expect.objectContaining({ Authorization: "Bearer desktop-session-token" }),
    });
  });

  it("edits desktop scope in the interface", async () => {
    window.pywebview = { api: { get_token: async () => "desktop-token" } };
    const fetchMock = vi.fn(async (path: string, _init?: RequestInit) => ({
      ok: true, status: 200,
      json: async () => path === "/api/settings/scope"
        ? { name: "lab", targets: ["local-node"], rate_limit: { requests: 10, per_seconds: 60 },
            prohibited_actions: [], time_windows: [], privileges: {} }
        : [],
    }));
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "设置" }));
    await screen.findByDisplayValue("local-node");
    fireEvent.change(screen.getByLabelText("授权目标（每行一个）"), {
      target: { value: "local-node\nsecond-node" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存授权范围" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/settings/scope", expect.objectContaining({ method: "PUT" }),
    ));
  });

  it("uses a saved vendor or gateway model from the interface", async () => {
    const fetchMock = vi.fn(async (path: string, _init?: RequestInit) => ({
      ok: true, status: 200,
      json: async () => path === "/api/settings/providers"
        ? [{ name: "gateway", kind: "openai_compatible", base_url: "http://127.0.0.1:8080/v1",
             model: "local-model", has_api_key: true }]
        : path === "/api/models/gateway/generate"
          ? { text: "模型已连接", usage: {} } : [],
    }));
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "模型" }));
    await screen.findByRole("option", { name: "gateway" });
    fireEvent.change(screen.getByLabelText("测试消息"), { target: { value: "你好" } });
    fireEvent.click(screen.getByRole("button", { name: "发送测试消息" }));

    expect(await screen.findByText("模型已连接")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/models/gateway/generate", expect.objectContaining({ method: "POST" }),
    );
  });

});
