import { z } from 'zod';
export declare const Point3DSchema: z.ZodObject<{
    x: z.ZodNumber;
    y: z.ZodNumber;
    z: z.ZodNumber;
}, "strip", z.ZodTypeAny, {
    x: number;
    y: number;
    z: number;
}, {
    x: number;
    y: number;
    z: number;
}>;
export declare const MacroNutrientsSchema: z.ZodObject<{
    caloriesKcal: z.ZodNumber;
    carbsG: z.ZodNumber;
    proteinG: z.ZodNumber;
    fatG: z.ZodNumber;
    sodiumMg: z.ZodNumber;
}, "strip", z.ZodTypeAny, {
    caloriesKcal: number;
    carbsG: number;
    proteinG: number;
    fatG: number;
    sodiumMg: number;
}, {
    caloriesKcal: number;
    carbsG: number;
    proteinG: number;
    fatG: number;
    sodiumMg: number;
}>;
export declare const SparsePointCloudSchema: z.ZodEffects<z.ZodObject<{
    count: z.ZodNumber;
    positions: z.ZodArray<z.ZodNumber, "many">;
    colors: z.ZodArray<z.ZodNumber, "many">;
}, "strip", z.ZodTypeAny, {
    count: number;
    positions: number[];
    colors: number[];
}, {
    count: number;
    positions: number[];
    colors: number[];
}>, {
    count: number;
    positions: number[];
    colors: number[];
}, {
    count: number;
    positions: number[];
    colors: number[];
}>;
declare const Candidate: z.ZodObject<{
    foodId: z.ZodString;
    foodName: z.ZodString;
    score: z.ZodNumber;
    densityGCm3: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
    weightG: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
    caloriesKcal: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
    carbsG: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
    proteinG: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
    fatG: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
    sodiumMg: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
}, "strip", z.ZodTypeAny, {
    foodId: string;
    foodName: string;
    score: number;
    caloriesKcal?: number | null | undefined;
    carbsG?: number | null | undefined;
    proteinG?: number | null | undefined;
    fatG?: number | null | undefined;
    sodiumMg?: number | null | undefined;
    densityGCm3?: number | null | undefined;
    weightG?: number | null | undefined;
}, {
    foodId: string;
    foodName: string;
    score: number;
    caloriesKcal?: number | null | undefined;
    carbsG?: number | null | undefined;
    proteinG?: number | null | undefined;
    fatG?: number | null | undefined;
    sodiumMg?: number | null | undefined;
    densityGCm3?: number | null | undefined;
    weightG?: number | null | undefined;
}>;
export declare const BoundingBox2DSchema: z.ZodObject<{
    ymin: z.ZodNumber;
    xmin: z.ZodNumber;
    ymax: z.ZodNumber;
    xmax: z.ZodNumber;
}, "strip", z.ZodTypeAny, {
    ymin: number;
    xmin: number;
    ymax: number;
    xmax: number;
}, {
    ymin: number;
    xmin: number;
    ymax: number;
    xmax: number;
}>;
export declare const BoundingBox3DSchema: z.ZodObject<{
    center: z.ZodObject<{
        x: z.ZodNumber;
        y: z.ZodNumber;
        z: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        x: number;
        y: number;
        z: number;
    }, {
        x: number;
        y: number;
        z: number;
    }>;
    dimensions: z.ZodObject<{
        x: z.ZodNumber;
        y: z.ZodNumber;
        z: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        x: number;
        y: number;
        z: number;
    }, {
        x: number;
        y: number;
        z: number;
    }>;
    rotations: z.ZodObject<{
        x: z.ZodNumber;
        y: z.ZodNumber;
        z: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        x: number;
        y: number;
        z: number;
    }, {
        x: number;
        y: number;
        z: number;
    }>;
    vertices: z.ZodArray<z.ZodObject<{
        x: z.ZodNumber;
        y: z.ZodNumber;
        z: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        x: number;
        y: number;
        z: number;
    }, {
        x: number;
        y: number;
        z: number;
    }>, "many">;
}, "strip", z.ZodTypeAny, {
    center: {
        x: number;
        y: number;
        z: number;
    };
    dimensions: {
        x: number;
        y: number;
        z: number;
    };
    rotations: {
        x: number;
        y: number;
        z: number;
    };
    vertices: {
        x: number;
        y: number;
        z: number;
    }[];
}, {
    center: {
        x: number;
        y: number;
        z: number;
    };
    dimensions: {
        x: number;
        y: number;
        z: number;
    };
    rotations: {
        x: number;
        y: number;
        z: number;
    };
    vertices: {
        x: number;
        y: number;
        z: number;
    }[];
}>;
export declare const FoodItemEstimationSchema: z.ZodObject<{
    id: z.ZodString;
    foodId: z.ZodString;
    foodName: z.ZodString;
    confidenceScore: z.ZodNumber;
    classificationConfidence: z.ZodNumber;
    geometryConfidence: z.ZodNumber;
    requiresConfirmation: z.ZodBoolean;
    topCandidates: z.ZodArray<z.ZodObject<{
        foodId: z.ZodString;
        foodName: z.ZodString;
        score: z.ZodNumber;
        densityGCm3: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
        weightG: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
        caloriesKcal: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
        carbsG: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
        proteinG: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
        fatG: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
        sodiumMg: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
    }, "strip", z.ZodTypeAny, {
        foodId: string;
        foodName: string;
        score: number;
        caloriesKcal?: number | null | undefined;
        carbsG?: number | null | undefined;
        proteinG?: number | null | undefined;
        fatG?: number | null | undefined;
        sodiumMg?: number | null | undefined;
        densityGCm3?: number | null | undefined;
        weightG?: number | null | undefined;
    }, {
        foodId: string;
        foodName: string;
        score: number;
        caloriesKcal?: number | null | undefined;
        carbsG?: number | null | undefined;
        proteinG?: number | null | undefined;
        fatG?: number | null | undefined;
        sodiumMg?: number | null | undefined;
        densityGCm3?: number | null | undefined;
        weightG?: number | null | undefined;
    }>, "many">;
    volumeCm3: z.ZodNumber;
    densityGCm3: z.ZodNumber;
    weightG: z.ZodNumber;
    caloriesKcal: z.ZodNumber;
    carbsG: z.ZodNumber;
    proteinG: z.ZodNumber;
    fatG: z.ZodNumber;
    sodiumMg: z.ZodNumber;
    bbox2d: z.ZodObject<{
        ymin: z.ZodNumber;
        xmin: z.ZodNumber;
        ymax: z.ZodNumber;
        xmax: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        ymin: number;
        xmin: number;
        ymax: number;
        xmax: number;
    }, {
        ymin: number;
        xmin: number;
        ymax: number;
        xmax: number;
    }>;
    bbox3d: z.ZodObject<{
        center: z.ZodObject<{
            x: z.ZodNumber;
            y: z.ZodNumber;
            z: z.ZodNumber;
        }, "strip", z.ZodTypeAny, {
            x: number;
            y: number;
            z: number;
        }, {
            x: number;
            y: number;
            z: number;
        }>;
        dimensions: z.ZodObject<{
            x: z.ZodNumber;
            y: z.ZodNumber;
            z: z.ZodNumber;
        }, "strip", z.ZodTypeAny, {
            x: number;
            y: number;
            z: number;
        }, {
            x: number;
            y: number;
            z: number;
        }>;
        rotations: z.ZodObject<{
            x: z.ZodNumber;
            y: z.ZodNumber;
            z: z.ZodNumber;
        }, "strip", z.ZodTypeAny, {
            x: number;
            y: number;
            z: number;
        }, {
            x: number;
            y: number;
            z: number;
        }>;
        vertices: z.ZodArray<z.ZodObject<{
            x: z.ZodNumber;
            y: z.ZodNumber;
            z: z.ZodNumber;
        }, "strip", z.ZodTypeAny, {
            x: number;
            y: number;
            z: number;
        }, {
            x: number;
            y: number;
            z: number;
        }>, "many">;
    }, "strip", z.ZodTypeAny, {
        center: {
            x: number;
            y: number;
            z: number;
        };
        dimensions: {
            x: number;
            y: number;
            z: number;
        };
        rotations: {
            x: number;
            y: number;
            z: number;
        };
        vertices: {
            x: number;
            y: number;
            z: number;
        }[];
    }, {
        center: {
            x: number;
            y: number;
            z: number;
        };
        dimensions: {
            x: number;
            y: number;
            z: number;
        };
        rotations: {
            x: number;
            y: number;
            z: number;
        };
        vertices: {
            x: number;
            y: number;
            z: number;
        }[];
    }>;
}, "strip", z.ZodTypeAny, {
    caloriesKcal: number;
    carbsG: number;
    proteinG: number;
    fatG: number;
    sodiumMg: number;
    foodId: string;
    foodName: string;
    densityGCm3: number;
    weightG: number;
    id: string;
    confidenceScore: number;
    classificationConfidence: number;
    geometryConfidence: number;
    requiresConfirmation: boolean;
    topCandidates: {
        foodId: string;
        foodName: string;
        score: number;
        caloriesKcal?: number | null | undefined;
        carbsG?: number | null | undefined;
        proteinG?: number | null | undefined;
        fatG?: number | null | undefined;
        sodiumMg?: number | null | undefined;
        densityGCm3?: number | null | undefined;
        weightG?: number | null | undefined;
    }[];
    volumeCm3: number;
    bbox2d: {
        ymin: number;
        xmin: number;
        ymax: number;
        xmax: number;
    };
    bbox3d: {
        center: {
            x: number;
            y: number;
            z: number;
        };
        dimensions: {
            x: number;
            y: number;
            z: number;
        };
        rotations: {
            x: number;
            y: number;
            z: number;
        };
        vertices: {
            x: number;
            y: number;
            z: number;
        }[];
    };
}, {
    caloriesKcal: number;
    carbsG: number;
    proteinG: number;
    fatG: number;
    sodiumMg: number;
    foodId: string;
    foodName: string;
    densityGCm3: number;
    weightG: number;
    id: string;
    confidenceScore: number;
    classificationConfidence: number;
    geometryConfidence: number;
    requiresConfirmation: boolean;
    topCandidates: {
        foodId: string;
        foodName: string;
        score: number;
        caloriesKcal?: number | null | undefined;
        carbsG?: number | null | undefined;
        proteinG?: number | null | undefined;
        fatG?: number | null | undefined;
        sodiumMg?: number | null | undefined;
        densityGCm3?: number | null | undefined;
        weightG?: number | null | undefined;
    }[];
    volumeCm3: number;
    bbox2d: {
        ymin: number;
        xmin: number;
        ymax: number;
        xmax: number;
    };
    bbox3d: {
        center: {
            x: number;
            y: number;
            z: number;
        };
        dimensions: {
            x: number;
            y: number;
            z: number;
        };
        rotations: {
            x: number;
            y: number;
            z: number;
        };
        vertices: {
            x: number;
            y: number;
            z: number;
        }[];
    };
}>;
export declare const DrugInteractionWarningSchema: z.ZodObject<{
    id: z.ZodString;
    drugBrandName: z.ZodString;
    drugIngredient: z.ZodString;
    triggerNutrientOrFood: z.ZodString;
    riskLevel: z.ZodString;
    detectedVia: z.ZodString;
    warningTitle: z.ZodString;
    warningMessage: z.ZodString;
    actionGuide: z.ZodString;
}, "strip", z.ZodTypeAny, {
    id: string;
    drugBrandName: string;
    drugIngredient: string;
    triggerNutrientOrFood: string;
    riskLevel: string;
    detectedVia: string;
    warningTitle: string;
    warningMessage: string;
    actionGuide: string;
}, {
    id: string;
    drugBrandName: string;
    drugIngredient: string;
    triggerNutrientOrFood: string;
    riskLevel: string;
    detectedVia: string;
    warningTitle: string;
    warningMessage: string;
    actionGuide: string;
}>;
export declare const DetectedPillInputSchema: z.ZodObject<{
    class_name: z.ZodString;
    class_id: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
    confidence: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
    box: z.ZodOptional<z.ZodNullable<z.ZodArray<z.ZodNumber, "many">>>;
}, "strip", z.ZodTypeAny, {
    class_name: string;
    class_id?: number | null | undefined;
    confidence?: number | null | undefined;
    box?: number[] | null | undefined;
}, {
    class_name: string;
    class_id?: number | null | undefined;
    confidence?: number | null | undefined;
    box?: number[] | null | undefined;
}>;
export declare const NutritionSummarySchema: z.ZodObject<{
    caloriesKcal: z.ZodNumber;
    carbsG: z.ZodNumber;
    proteinG: z.ZodNumber;
    fatG: z.ZodNumber;
    sodiumMg: z.ZodNumber;
}, "strip", z.ZodTypeAny, {
    caloriesKcal: number;
    carbsG: number;
    proteinG: number;
    fatG: number;
    sodiumMg: number;
}, {
    caloriesKcal: number;
    carbsG: number;
    proteinG: number;
    fatG: number;
    sodiumMg: number;
}>;
export declare const PlaneEquationSchema: z.ZodObject<{
    a: z.ZodNumber;
    b: z.ZodNumber;
    c: z.ZodNumber;
    d: z.ZodNumber;
}, "strip", z.ZodTypeAny, {
    a: number;
    b: number;
    c: number;
    d: number;
}, {
    a: number;
    b: number;
    c: number;
    d: number;
}>;
export declare const Visualization3DSchema: z.ZodObject<{
    pointCloud: z.ZodEffects<z.ZodObject<{
        count: z.ZodNumber;
        positions: z.ZodArray<z.ZodNumber, "many">;
        colors: z.ZodArray<z.ZodNumber, "many">;
    }, "strip", z.ZodTypeAny, {
        count: number;
        positions: number[];
        colors: number[];
    }, {
        count: number;
        positions: number[];
        colors: number[];
    }>, {
        count: number;
        positions: number[];
        colors: number[];
    }, {
        count: number;
        positions: number[];
        colors: number[];
    }>;
}, "strip", z.ZodTypeAny, {
    pointCloud: {
        count: number;
        positions: number[];
        colors: number[];
    };
}, {
    pointCloud: {
        count: number;
        positions: number[];
        colors: number[];
    };
}>;
export declare const MealEstimateResponseSchema: z.ZodObject<{
    mealId: z.ZodString;
    isPersisted: z.ZodBoolean;
    requiresConfirmation: z.ZodBoolean;
    imageUrl: z.ZodString;
    isCalibrated: z.ZodBoolean;
    focalLengthMm: z.ZodNumber;
    groundPlane: z.ZodObject<{
        a: z.ZodNumber;
        b: z.ZodNumber;
        c: z.ZodNumber;
        d: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        a: number;
        b: number;
        c: number;
        d: number;
    }, {
        a: number;
        b: number;
        c: number;
        d: number;
    }>;
    totalNutrition: z.ZodObject<{
        caloriesKcal: z.ZodNumber;
        carbsG: z.ZodNumber;
        proteinG: z.ZodNumber;
        fatG: z.ZodNumber;
        sodiumMg: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        caloriesKcal: number;
        carbsG: number;
        proteinG: number;
        fatG: number;
        sodiumMg: number;
    }, {
        caloriesKcal: number;
        carbsG: number;
        proteinG: number;
        fatG: number;
        sodiumMg: number;
    }>;
    foodItems: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        foodId: z.ZodString;
        foodName: z.ZodString;
        confidenceScore: z.ZodNumber;
        classificationConfidence: z.ZodNumber;
        geometryConfidence: z.ZodNumber;
        requiresConfirmation: z.ZodBoolean;
        topCandidates: z.ZodArray<z.ZodObject<{
            foodId: z.ZodString;
            foodName: z.ZodString;
            score: z.ZodNumber;
            densityGCm3: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
            weightG: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
            caloriesKcal: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
            carbsG: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
            proteinG: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
            fatG: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
            sodiumMg: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
        }, "strip", z.ZodTypeAny, {
            foodId: string;
            foodName: string;
            score: number;
            caloriesKcal?: number | null | undefined;
            carbsG?: number | null | undefined;
            proteinG?: number | null | undefined;
            fatG?: number | null | undefined;
            sodiumMg?: number | null | undefined;
            densityGCm3?: number | null | undefined;
            weightG?: number | null | undefined;
        }, {
            foodId: string;
            foodName: string;
            score: number;
            caloriesKcal?: number | null | undefined;
            carbsG?: number | null | undefined;
            proteinG?: number | null | undefined;
            fatG?: number | null | undefined;
            sodiumMg?: number | null | undefined;
            densityGCm3?: number | null | undefined;
            weightG?: number | null | undefined;
        }>, "many">;
        volumeCm3: z.ZodNumber;
        densityGCm3: z.ZodNumber;
        weightG: z.ZodNumber;
        caloriesKcal: z.ZodNumber;
        carbsG: z.ZodNumber;
        proteinG: z.ZodNumber;
        fatG: z.ZodNumber;
        sodiumMg: z.ZodNumber;
        bbox2d: z.ZodObject<{
            ymin: z.ZodNumber;
            xmin: z.ZodNumber;
            ymax: z.ZodNumber;
            xmax: z.ZodNumber;
        }, "strip", z.ZodTypeAny, {
            ymin: number;
            xmin: number;
            ymax: number;
            xmax: number;
        }, {
            ymin: number;
            xmin: number;
            ymax: number;
            xmax: number;
        }>;
        bbox3d: z.ZodObject<{
            center: z.ZodObject<{
                x: z.ZodNumber;
                y: z.ZodNumber;
                z: z.ZodNumber;
            }, "strip", z.ZodTypeAny, {
                x: number;
                y: number;
                z: number;
            }, {
                x: number;
                y: number;
                z: number;
            }>;
            dimensions: z.ZodObject<{
                x: z.ZodNumber;
                y: z.ZodNumber;
                z: z.ZodNumber;
            }, "strip", z.ZodTypeAny, {
                x: number;
                y: number;
                z: number;
            }, {
                x: number;
                y: number;
                z: number;
            }>;
            rotations: z.ZodObject<{
                x: z.ZodNumber;
                y: z.ZodNumber;
                z: z.ZodNumber;
            }, "strip", z.ZodTypeAny, {
                x: number;
                y: number;
                z: number;
            }, {
                x: number;
                y: number;
                z: number;
            }>;
            vertices: z.ZodArray<z.ZodObject<{
                x: z.ZodNumber;
                y: z.ZodNumber;
                z: z.ZodNumber;
            }, "strip", z.ZodTypeAny, {
                x: number;
                y: number;
                z: number;
            }, {
                x: number;
                y: number;
                z: number;
            }>, "many">;
        }, "strip", z.ZodTypeAny, {
            center: {
                x: number;
                y: number;
                z: number;
            };
            dimensions: {
                x: number;
                y: number;
                z: number;
            };
            rotations: {
                x: number;
                y: number;
                z: number;
            };
            vertices: {
                x: number;
                y: number;
                z: number;
            }[];
        }, {
            center: {
                x: number;
                y: number;
                z: number;
            };
            dimensions: {
                x: number;
                y: number;
                z: number;
            };
            rotations: {
                x: number;
                y: number;
                z: number;
            };
            vertices: {
                x: number;
                y: number;
                z: number;
            }[];
        }>;
    }, "strip", z.ZodTypeAny, {
        caloriesKcal: number;
        carbsG: number;
        proteinG: number;
        fatG: number;
        sodiumMg: number;
        foodId: string;
        foodName: string;
        densityGCm3: number;
        weightG: number;
        id: string;
        confidenceScore: number;
        classificationConfidence: number;
        geometryConfidence: number;
        requiresConfirmation: boolean;
        topCandidates: {
            foodId: string;
            foodName: string;
            score: number;
            caloriesKcal?: number | null | undefined;
            carbsG?: number | null | undefined;
            proteinG?: number | null | undefined;
            fatG?: number | null | undefined;
            sodiumMg?: number | null | undefined;
            densityGCm3?: number | null | undefined;
            weightG?: number | null | undefined;
        }[];
        volumeCm3: number;
        bbox2d: {
            ymin: number;
            xmin: number;
            ymax: number;
            xmax: number;
        };
        bbox3d: {
            center: {
                x: number;
                y: number;
                z: number;
            };
            dimensions: {
                x: number;
                y: number;
                z: number;
            };
            rotations: {
                x: number;
                y: number;
                z: number;
            };
            vertices: {
                x: number;
                y: number;
                z: number;
            }[];
        };
    }, {
        caloriesKcal: number;
        carbsG: number;
        proteinG: number;
        fatG: number;
        sodiumMg: number;
        foodId: string;
        foodName: string;
        densityGCm3: number;
        weightG: number;
        id: string;
        confidenceScore: number;
        classificationConfidence: number;
        geometryConfidence: number;
        requiresConfirmation: boolean;
        topCandidates: {
            foodId: string;
            foodName: string;
            score: number;
            caloriesKcal?: number | null | undefined;
            carbsG?: number | null | undefined;
            proteinG?: number | null | undefined;
            fatG?: number | null | undefined;
            sodiumMg?: number | null | undefined;
            densityGCm3?: number | null | undefined;
            weightG?: number | null | undefined;
        }[];
        volumeCm3: number;
        bbox2d: {
            ymin: number;
            xmin: number;
            ymax: number;
            xmax: number;
        };
        bbox3d: {
            center: {
                x: number;
                y: number;
                z: number;
            };
            dimensions: {
                x: number;
                y: number;
                z: number;
            };
            rotations: {
                x: number;
                y: number;
                z: number;
            };
            vertices: {
                x: number;
                y: number;
                z: number;
            }[];
        };
    }>, "many">;
    drugWarnings: z.ZodDefault<z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        drugBrandName: z.ZodString;
        drugIngredient: z.ZodString;
        triggerNutrientOrFood: z.ZodString;
        riskLevel: z.ZodString;
        detectedVia: z.ZodString;
        warningTitle: z.ZodString;
        warningMessage: z.ZodString;
        actionGuide: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        id: string;
        drugBrandName: string;
        drugIngredient: string;
        triggerNutrientOrFood: string;
        riskLevel: string;
        detectedVia: string;
        warningTitle: string;
        warningMessage: string;
        actionGuide: string;
    }, {
        id: string;
        drugBrandName: string;
        drugIngredient: string;
        triggerNutrientOrFood: string;
        riskLevel: string;
        detectedVia: string;
        warningTitle: string;
        warningMessage: string;
        actionGuide: string;
    }>, "many">>;
    detectedPills: z.ZodOptional<z.ZodArray<z.ZodObject<{
        class_name: z.ZodString;
        class_id: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
        confidence: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
        box: z.ZodOptional<z.ZodNullable<z.ZodArray<z.ZodNumber, "many">>>;
    }, "strip", z.ZodTypeAny, {
        class_name: string;
        class_id?: number | null | undefined;
        confidence?: number | null | undefined;
        box?: number[] | null | undefined;
    }, {
        class_name: string;
        class_id?: number | null | undefined;
        confidence?: number | null | undefined;
        box?: number[] | null | undefined;
    }>, "many">>;
    visualization3d: z.ZodObject<{
        pointCloud: z.ZodEffects<z.ZodObject<{
            count: z.ZodNumber;
            positions: z.ZodArray<z.ZodNumber, "many">;
            colors: z.ZodArray<z.ZodNumber, "many">;
        }, "strip", z.ZodTypeAny, {
            count: number;
            positions: number[];
            colors: number[];
        }, {
            count: number;
            positions: number[];
            colors: number[];
        }>, {
            count: number;
            positions: number[];
            colors: number[];
        }, {
            count: number;
            positions: number[];
            colors: number[];
        }>;
    }, "strip", z.ZodTypeAny, {
        pointCloud: {
            count: number;
            positions: number[];
            colors: number[];
        };
    }, {
        pointCloud: {
            count: number;
            positions: number[];
            colors: number[];
        };
    }>;
    processedAt: z.ZodString;
    inferenceLatencyMs: z.ZodNumber;
}, "strip", z.ZodTypeAny, {
    requiresConfirmation: boolean;
    mealId: string;
    isPersisted: boolean;
    imageUrl: string;
    isCalibrated: boolean;
    focalLengthMm: number;
    groundPlane: {
        a: number;
        b: number;
        c: number;
        d: number;
    };
    totalNutrition: {
        caloriesKcal: number;
        carbsG: number;
        proteinG: number;
        fatG: number;
        sodiumMg: number;
    };
    foodItems: {
        caloriesKcal: number;
        carbsG: number;
        proteinG: number;
        fatG: number;
        sodiumMg: number;
        foodId: string;
        foodName: string;
        densityGCm3: number;
        weightG: number;
        id: string;
        confidenceScore: number;
        classificationConfidence: number;
        geometryConfidence: number;
        requiresConfirmation: boolean;
        topCandidates: {
            foodId: string;
            foodName: string;
            score: number;
            caloriesKcal?: number | null | undefined;
            carbsG?: number | null | undefined;
            proteinG?: number | null | undefined;
            fatG?: number | null | undefined;
            sodiumMg?: number | null | undefined;
            densityGCm3?: number | null | undefined;
            weightG?: number | null | undefined;
        }[];
        volumeCm3: number;
        bbox2d: {
            ymin: number;
            xmin: number;
            ymax: number;
            xmax: number;
        };
        bbox3d: {
            center: {
                x: number;
                y: number;
                z: number;
            };
            dimensions: {
                x: number;
                y: number;
                z: number;
            };
            rotations: {
                x: number;
                y: number;
                z: number;
            };
            vertices: {
                x: number;
                y: number;
                z: number;
            }[];
        };
    }[];
    drugWarnings: {
        id: string;
        drugBrandName: string;
        drugIngredient: string;
        triggerNutrientOrFood: string;
        riskLevel: string;
        detectedVia: string;
        warningTitle: string;
        warningMessage: string;
        actionGuide: string;
    }[];
    visualization3d: {
        pointCloud: {
            count: number;
            positions: number[];
            colors: number[];
        };
    };
    processedAt: string;
    inferenceLatencyMs: number;
    detectedPills?: {
        class_name: string;
        class_id?: number | null | undefined;
        confidence?: number | null | undefined;
        box?: number[] | null | undefined;
    }[] | undefined;
}, {
    requiresConfirmation: boolean;
    mealId: string;
    isPersisted: boolean;
    imageUrl: string;
    isCalibrated: boolean;
    focalLengthMm: number;
    groundPlane: {
        a: number;
        b: number;
        c: number;
        d: number;
    };
    totalNutrition: {
        caloriesKcal: number;
        carbsG: number;
        proteinG: number;
        fatG: number;
        sodiumMg: number;
    };
    foodItems: {
        caloriesKcal: number;
        carbsG: number;
        proteinG: number;
        fatG: number;
        sodiumMg: number;
        foodId: string;
        foodName: string;
        densityGCm3: number;
        weightG: number;
        id: string;
        confidenceScore: number;
        classificationConfidence: number;
        geometryConfidence: number;
        requiresConfirmation: boolean;
        topCandidates: {
            foodId: string;
            foodName: string;
            score: number;
            caloriesKcal?: number | null | undefined;
            carbsG?: number | null | undefined;
            proteinG?: number | null | undefined;
            fatG?: number | null | undefined;
            sodiumMg?: number | null | undefined;
            densityGCm3?: number | null | undefined;
            weightG?: number | null | undefined;
        }[];
        volumeCm3: number;
        bbox2d: {
            ymin: number;
            xmin: number;
            ymax: number;
            xmax: number;
        };
        bbox3d: {
            center: {
                x: number;
                y: number;
                z: number;
            };
            dimensions: {
                x: number;
                y: number;
                z: number;
            };
            rotations: {
                x: number;
                y: number;
                z: number;
            };
            vertices: {
                x: number;
                y: number;
                z: number;
            }[];
        };
    }[];
    visualization3d: {
        pointCloud: {
            count: number;
            positions: number[];
            colors: number[];
        };
    };
    processedAt: string;
    inferenceLatencyMs: number;
    drugWarnings?: {
        id: string;
        drugBrandName: string;
        drugIngredient: string;
        triggerNutrientOrFood: string;
        riskLevel: string;
        detectedVia: string;
        warningTitle: string;
        warningMessage: string;
        actionGuide: string;
    }[] | undefined;
    detectedPills?: {
        class_name: string;
        class_id?: number | null | undefined;
        confidence?: number | null | undefined;
        box?: number[] | null | undefined;
    }[] | undefined;
}>;
export declare const MealConfirmRequestSchema: z.ZodObject<{
    mealId: z.ZodString;
    corrections: z.ZodArray<z.ZodObject<{
        foodItemId: z.ZodString;
        correctedWeightG: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        foodItemId: string;
        correctedWeightG: number;
    }, {
        foodItemId: string;
        correctedWeightG: number;
    }>, "many">;
}, "strip", z.ZodTypeAny, {
    mealId: string;
    corrections: {
        foodItemId: string;
        correctedWeightG: number;
    }[];
}, {
    mealId: string;
    corrections: {
        foodItemId: string;
        correctedWeightG: number;
    }[];
}>;
export type Point3D = z.infer<typeof Point3DSchema>;
export type MacroNutrients = z.infer<typeof MacroNutrientsSchema>;
export type SparsePointCloudPayload = z.infer<typeof SparsePointCloudSchema>;
export type FoodCandidate = z.infer<typeof Candidate>;
export type BoundingBox2D = z.infer<typeof BoundingBox2DSchema>;
export type BoundingBox3D = z.infer<typeof BoundingBox3DSchema>;
export type FoodItemEstimation = z.infer<typeof FoodItemEstimationSchema>;
export type DrugInteractionWarning = z.infer<typeof DrugInteractionWarningSchema>;
export type DetectedPillInput = z.infer<typeof DetectedPillInputSchema>;
export type NutritionSummary = z.infer<typeof NutritionSummarySchema>;
export type PlaneEquation = z.infer<typeof PlaneEquationSchema>;
export type Visualization3D = z.infer<typeof Visualization3DSchema>;
export type MealEstimateResponse = z.infer<typeof MealEstimateResponseSchema>;
export type MealConfirmRequest = z.infer<typeof MealConfirmRequestSchema>;
export {};
