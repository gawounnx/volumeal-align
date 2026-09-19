import { z } from 'zod';
export declare const FrontendEnvironmentSchema: z.ZodObject<{
    NODE_ENV: z.ZodDefault<z.ZodEnum<["development", "test", "production"]>>;
    HOST: z.ZodDefault<z.ZodString>;
    PORT: z.ZodDefault<z.ZodNumber>;
    NEXT_PUBLIC_API_BASE_URL: z.ZodString;
    NEXT_PUBLIC_API_MOCKING: z.ZodDefault<z.ZodEnum<["true", "false"]>>;
}, "strip", z.ZodTypeAny, {
    NODE_ENV: "development" | "test" | "production";
    HOST: string;
    PORT: number;
    NEXT_PUBLIC_API_BASE_URL: string;
    NEXT_PUBLIC_API_MOCKING: "true" | "false";
}, {
    NEXT_PUBLIC_API_BASE_URL: string;
    NODE_ENV?: "development" | "test" | "production" | undefined;
    HOST?: string | undefined;
    PORT?: number | undefined;
    NEXT_PUBLIC_API_MOCKING?: "true" | "false" | undefined;
}>;
export declare function validateFrontendEnv(v: Record<string, unknown>): {
    NODE_ENV: "development" | "test" | "production";
    HOST: string;
    PORT: number;
    NEXT_PUBLIC_API_BASE_URL: string;
    NEXT_PUBLIC_API_MOCKING: "true" | "false";
};
